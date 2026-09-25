"""Step 19 — bootstrap confidence intervals for the sampled quantities.

Which quantities get an interval, and which do not, is a deliberate choice:

  * The registry census (35,388 servers, 114,604 versions) is the whole
    population, not a sample. Reporting a confidence interval there would imply
    sampling error that does not exist, so those figures are reported as exact
    counts and shares.
  * Figures computed from a drawn sample do carry sampling error, and get a
    percentile bootstrap interval: the 200 coded tool definitions, the 150
    coded servers, the 1,200-package extraction sample and the 914-repository
    sample.
  * The credential shares are computed over 174,265 variables declared by 7,515
    servers. Variables cluster within a server, so the bootstrap resamples
    servers rather than variables; resampling variables would understate the
    interval.

Writes results/tables/t31_bootstrap_intervals.csv.
"""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import pandas as pd  # noqa: E402

from mcpstudy import analysis, config, registry  # noqa: E402

VALID = os.path.join(config.RESULTS_DIR, "validation")
N = 10000
SEED = 20260928


def percentile_ci(values):
    values = sorted(values)
    lo = values[int(0.025 * len(values))]
    hi = values[int(0.975 * len(values)) - 1]
    return lo, hi


def boot_proportion(flags, n=N, seed=SEED, cluster=None):
    """Percentile bootstrap for a proportion, optionally clustered."""
    rng = random.Random(seed)
    if cluster is None:
        k = len(flags)
        draws = []
        for _ in range(n):
            s = 0
            for _ in range(k):
                s += flags[rng.randrange(k)]
            draws.append(100.0 * s / k)
    else:
        # Cluster bootstrap: resample clusters, keep all rows inside each.
        groups = {}
        for flag, key in zip(flags, cluster):
            groups.setdefault(key, []).append(flag)
        keys = list(groups)
        draws = []
        for _ in range(n):
            num = den = 0
            for _ in range(len(keys)):
                rows = groups[keys[rng.randrange(len(keys))]]
                num += sum(rows)
                den += len(rows)
            draws.append(100.0 * num / den)
    return percentile_ci(draws)


def main():
    rows = []

    def add(label, point, ci, n, basis):
        rows.append({
            "quantity": label,
            "value_pct": round(point, 1),
            "ci95_low": round(ci[0], 1),
            "ci95_high": round(ci[1], 1),
            "n": n,
            "basis": basis,
        })

    # --- human coding, Part C (200 tool definitions) -------------------------
    part_c = pd.read_csv(os.path.join(VALID, "part_c_codes.csv"))
    n_c = len(part_c)
    for label, column, target in [
        ("description states the purpose", "desc_states_purpose", "yes"),
        ("description explains the inputs", "desc_states_inputs", "yes"),
        ("description names side effects", "desc_names_side_effects", "yes"),
        ("description states when to use", "desc_states_when_to_use", "yes"),
    ]:
        flags = (part_c[column].astype(str).str.strip() == target).astype(int).tolist()
        point = 100.0 * sum(flags) / len(flags)
        add(label, point, boot_proportion(flags), n_c, "coded tool definitions")
    flags = (part_c["ambiguous_count"] > 0).astype(int).tolist()
    add("confusable with a sibling tool", 100.0 * sum(flags) / len(flags),
        boot_proportion(flags), n_c, "coded tool definitions")

    # --- human coding, Part B (150 servers) ----------------------------------
    part_b = pd.read_csv(os.path.join(VALID, "part_b_codes.csv"))
    n_b = len(part_b)
    for label, column, target in [
        ("authentication mechanism identified", "auth_mechanism", None),
        ("no authentication required", "auth_mechanism", "none"),
        ("write capability", "write_capability", "yes"),
        ("broad scope", "scope_breadth", "broad"),
    ]:
        if target is None:
            flags = (~part_b[column].astype(str).str.strip()
                     .isin(["", "unclear", "undetermined"])).astype(int).tolist()
        else:
            flags = (part_b[column].astype(str).str.strip() == target).astype(int).tolist()
        add(label, 100.0 * sum(flags) / len(flags), boot_proportion(flags),
            n_b, "coded servers")
    flags = ((part_b["scope_breadth"].astype(str).str.strip() == "broad")
             & (part_b["write_capability"].astype(str).str.strip() == "yes")
             ).astype(int).tolist()
    add("broad scope and write capability", 100.0 * sum(flags) / len(flags),
        boot_proportion(flags), n_b, "coded servers")

    # --- extraction sample (1,200 packages) ----------------------------------
    cov = []
    with open(config.out("tool_extraction_coverage.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                cov.append(__import__("json").loads(line))
    flags = [1 if c.get("tools_found", 0) > 0 else 0 for c in cov]
    add("packages yielding at least one tool", 100.0 * sum(flags) / len(flags),
        boot_proportion(flags), len(flags), "sampled packages")

    # --- repository sample (914 servers) -------------------------------------
    repos = pd.read_json(config.out("github_repos.jsonl"), lines=True)
    versions = pd.DataFrame(registry.flatten(registry.load_entries()))
    latest = pd.DataFrame(registry.latest_versions(versions.to_dict("records")))
    latest["version_count"] = latest["name"].map(versions.groupby("name").size())
    import re

    def repo_key(url):
        m = re.match(r"^(?:https?://)?(?:www\.)?github\.com[/:]([^/]+)/([^/#?]+)",
                     str(url or ""), re.IGNORECASE)
        return "%s/%s" % (m.group(1), m.group(2).replace(".git", "")) if m else None

    latest["repo"] = latest["repository_url"].apply(repo_key)
    fetched = set(repos.loc[repos["status"] == "ok", "repo_full_name"])
    releases = pd.read_json(config.out("github_releases.jsonl"), lines=True)
    counts = releases.groupby("repo_full_name").size().rename("gh_releases")
    frame = latest.dropna(subset=["repo"])
    frame = frame[frame["repo"].isin(fetched)]
    frame = frame.merge(counts, left_on="repo", right_index=True, how="left")
    frame["gh_releases"] = frame["gh_releases"].fillna(0).astype(int)
    flags = (frame["gh_releases"] == 0).astype(int).tolist()
    add("servers with no tagged release", 100.0 * sum(flags) / len(flags),
        boot_proportion(flags), len(flags), "sampled repositories")

    # Spearman rank agreement between the two release signals. Computed on the
    # repository sample, so it carries sampling error and gets an interval.
    pairs = list(zip(frame["version_count"].tolist(),
                     frame["gh_releases"].tolist()))
    rng = random.Random(SEED)
    draws = []
    for _ in range(N):
        sample = [pairs[rng.randrange(len(pairs))] for _ in range(len(pairs))]
        a = pd.Series([p[0] for p in sample])
        b = pd.Series([p[1] for p in sample])
        if a.nunique() > 1 and b.nunique() > 1:
            draws.append(a.corr(b, method="spearman"))
    draws.sort()
    point = frame["version_count"].corr(frame["gh_releases"], method="spearman")
    rows.append({
        "quantity": "Spearman correlation, registry versions vs releases",
        "value_pct": round(point, 3),
        "ci95_low": round(draws[int(0.025 * len(draws))], 3),
        "ci95_high": round(draws[int(0.975 * len(draws)) - 1], 3),
        "n": len(pairs),
        "basis": "sampled repositories",
    })

    # --- credential shares, clustered by server ------------------------------
    #
    # Both credential rules are bootstrapped, because both are quoted: the
    # whole-word rule is the paper's lower bound and the permissive substring
    # rule is its upper bound, and the gap between them is a reported result.
    # Two bases are computed because counting every published version lets a
    # server that republishes often contribute many times, while counting only
    # the latest version describes what a client sees today.
    #
    # The rule lives in mcpstudy.analysis so the interval cannot drift away
    # from the point estimate the manuscript quotes.
    entries = registry.load_entries()
    env = pd.DataFrame(registry.extract_environment_variables(entries))
    verdicts = env.apply(
        lambda row: analysis.classify_credential(row.get("var_name"),
                                                 row.get("var_description"))[0],
        axis=1,
    )
    env["credential_tier"] = verdicts
    env["audit_demoted"] = env["var_name"].map(
        lambda v: v in analysis.AUDIT_NON_CREDENTIAL
    )
    env["credential_named"] = env["credential_tier"].notna() & ~env["audit_demoted"]
    name_lower = env["var_name"].fillna("").str.lower()
    desc_lower = env["var_description"].fillna("").str.lower()
    env["permissive"] = (
        name_lower.apply(lambda v: any(h in v for h in analysis.PERMISSIVE_HINTS))
        | desc_lower.apply(lambda v: any(h in v for h in analysis.PERMISSIVE_HINTS))
    )

    for basis, frame_env in (("all published versions", env),
                             ("latest version only", env[env["is_latest"]])):
        for label, column in (("whole-word rule", "credential_named"),
                              ("permissive substring rule", "permissive")):
            flagged = frame_env[frame_env[column]]
            flags = (~flagged["is_secret"]).astype(int).tolist()
            clusters = flagged["server_name"].tolist()
            add("unflagged credential names, of credential-named (%s, %s)"
                % (label, basis),
                100.0 * sum(flags) / len(flags),
                boot_proportion(flags, cluster=clusters), len(flags), basis)
            # The share of every declared variable, which is what the
            # manuscript quotes.
            all_flags = ((frame_env[column] & ~frame_env["is_secret"])
                         .astype(int)).tolist()
            all_clusters = frame_env["server_name"].tolist()
            add("unflagged credential names, of all declared (%s, %s)"
                % (label, basis),
                100.0 * sum(all_flags) / len(all_flags),
                boot_proportion(all_flags, cluster=all_clusters),
                len(all_flags), basis)

    out = pd.DataFrame(rows)
    path = os.path.join(config.TABLES_DIR, "t31_bootstrap_intervals.csv")
    out.to_csv(path, index=False, encoding="utf-8")
    print("%-46s %7s %-15s %8s" % ("quantity", "value", "95% CI", "n"))
    print("-" * 82)
    for _, r in out.iterrows():
        print("%-46s %6.1f%% [%5.1f, %5.1f] %8d"
              % (r["quantity"], r["value_pct"], r["ci95_low"], r["ci95_high"], r["n"]))
    print("\nwrote %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
