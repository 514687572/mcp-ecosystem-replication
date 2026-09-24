"""Step 16 — test validity threat T1 directly.

T1 says registry timestamps and version counts record registry ingestion, not
author release practice, so "time between releases" measured from the registry
cannot be trusted on its own. This script tests that claim against an
independent signal: the tagged releases a repository actually publishes on
GitHub.

Output: results/tables/t29_registry_versions_vs_github_releases.csv
        results/tables/t30_release_signal_agreement.csv
        results/validation/t1_note.md
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import pandas as pd  # noqa: E402

from mcpstudy import config, registry  # noqa: E402


def repo_key(url):
    match = re.match(
        r"^(?:https?://)?(?:www\.)?github\.com[/:]([^/]+)/([^/#?]+)",
        str(url or ""), re.IGNORECASE,
    )
    if not match:
        return None
    return "%s/%s" % (match.group(1), match.group(2).replace(".git", ""))


def main():
    config.load()
    tables = config.TABLES_DIR

    versions = pd.DataFrame(registry.flatten(registry.load_entries()))
    latest = pd.DataFrame(registry.latest_versions(versions.to_dict("records")))
    latest["version_count"] = latest["name"].map(versions.groupby("name").size())
    latest["repo"] = latest["repository_url"].apply(repo_key)

    repos = pd.read_json(config.out("github_repos.jsonl"), lines=True)
    releases = pd.read_json(config.out("github_releases.jsonl"), lines=True)

    fetched = set(repos.loc[repos["status"] == "ok", "repo_full_name"])
    release_counts = releases.groupby("repo_full_name").size().rename("gh_releases")

    # Left join, so a repository that publishes no tagged releases counts as 0
    # rather than dropping out of the analysis. An inner join here would have
    # silently reported "0% of servers have no GitHub releases".
    frame = latest.dropna(subset=["repo"]).copy()
    frame = frame[frame["repo"].isin(fetched)]
    frame = frame.merge(release_counts, left_on="repo", right_index=True, how="left")
    frame["gh_releases"] = frame["gh_releases"].fillna(0).astype(int)
    frame["no_gh_release"] = frame["gh_releases"] == 0

    total = len(frame)
    both = int((frame["version_count"] > 0).sum())

    def pct(n, d):
        return round(100.0 * n / d, 1) if d else 0.0

    summary = pd.DataFrame(
        [
            ("servers whose repository was resolved", total),
            ("... with at least one registry version", both),
            ("... with zero GitHub releases",
             int(frame["no_gh_release"].sum())),
            ("share with zero GitHub releases (%)",
             pct(int(frame["no_gh_release"].sum()), total)),
            ("median registry versions",
             float(frame["version_count"].median())),
            ("median GitHub releases",
             float(frame["gh_releases"].median())),
            ("mean registry versions",
             round(float(frame["version_count"].mean()), 2)),
            ("mean GitHub releases",
             round(float(frame["gh_releases"].mean()), 2)),
            ("servers where GitHub releases > registry versions",
             int((frame["gh_releases"] > frame["version_count"]).sum())),
            ("servers where the two counts are equal",
             int((frame["gh_releases"] == frame["version_count"]).sum())),
            ("servers where registry versions > GitHub releases",
             int((frame["version_count"] > frame["gh_releases"]).sum())),
            ("Spearman correlation between the two counts",
             round(frame["version_count"].corr(frame["gh_releases"],
                                                method="spearman"), 3)),
        ],
        columns=["metric", "value"],
    )

    # Agreement bands: how much does the registry understate release activity?
    bands = []
    for label, mask in [
        ("GitHub releases exceed registry versions", frame["gh_releases"] > frame["version_count"]),
        ("counts agree exactly", frame["gh_releases"] == frame["version_count"]),
        ("registry versions exceed GitHub releases", frame["version_count"] > frame["gh_releases"]),
        ("registry understates by 2x or more",
         frame["gh_releases"] >= 2 * frame["version_count"].replace(0, 1)),
    ]:
        n = int(mask.sum())
        bands.append({"pattern": label, "servers": n, "share_pct": pct(n, total)})
    band_frame = pd.DataFrame(bands)

    summary.to_csv(os.path.join(tables, "t29_registry_versions_vs_github_releases.csv"),
                   index=False, encoding="utf-8")
    band_frame.to_csv(os.path.join(tables, "t30_release_signal_agreement.csv"),
                      index=False, encoding="utf-8")

    def value_of(metric):
        found = summary.loc[summary["metric"] == metric, "value"]
        return found.iloc[0] if len(found) else "n/a"

    note_path = os.path.join(config.RESULTS_DIR, "validation", "t1_note.md")
    with open(note_path, "w", encoding="utf-8") as fh:
        fh.write("# Validity threat T1 — tested against GitHub releases\n\n")
        fh.write("T1 claims registry version counts record registry ingestion, not\n")
        fh.write("author release practice. Tested on the %d servers whose repository\n"
                 "was resolved and fetched in the seeded GitHub sample.\n\n" % total)
        for _, row in summary.iterrows():
            fh.write("- %s: **%s**\n" % (row["metric"], row["value"]))
        fh.write("\n## Reading\n\n")
        fh.write(
            "The two signals do not measure the same thing, so neither is a clean\n"
            "proxy for release cadence.\n\n"
            "Most servers never tag a GitHub release at all: **%s%%** have zero\n"
            "tagged releases while still publishing to the registry, which is why\n"
            "the median GitHub release count is **%s** against a median of **%s**\n"
            "registry versions. GitHub releases therefore cannot serve as a ground\n"
            "truth for the whole population.\n\n"
            "For the minority that do tag releases the relationship runs the other\n"
            "way: GitHub release counts exceed registry version counts for **%s%%**\n"
            "of servers, and the registry understates GitHub releases by two times\n"
            "or more for **%s%%**. Rank agreement is weak to moderate throughout\n"
            "(Spearman **%s**).\n\n"
            "Consequence for the paper: the registry is usable for *presence*\n"
            "questions — whether a server ships updates at all, and in which month\n"
            "it first appeared — but not for *cadence* questions. Every timing claim\n"
            "is phrased accordingly, and the sub-day median inter-version gap is\n"
            "reported as an ingestion artefact rather than a release rhythm.\n"
            % (
                value_of("share with zero GitHub releases (%)"),
                value_of("median GitHub releases"),
                value_of("median registry versions"),
                pct(int((frame["gh_releases"] > frame["version_count"]).sum()), total),
                pct(int((frame["gh_releases"] >= 2 * frame["version_count"].replace(0, 1)).sum()), total),
                value_of("Spearman correlation between the two counts"),
            )
        )
        fh.write("\n## Method note\n\n")
        fh.write("The join is a left join: a repository that publishes no tagged\n")
        fh.write("releases counts as zero rather than dropping out. An inner join\n")
        fh.write("would have hidden the largest single group in the data.\n")

    for _, row in summary.iterrows():
        print("  %-54s %s" % (row["metric"], row["value"]))
    print()
    for _, row in band_frame.iterrows():
        print("  %-42s %4d  (%.1f%%)"
              % (row["pattern"], row["servers"], row["share_pct"]))
    print("\nwrote results/tables/t29, t30 and results/validation/t1_note.md")


if __name__ == "__main__":
    main()
