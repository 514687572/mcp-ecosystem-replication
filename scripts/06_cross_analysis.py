"""Step 6 — cross-source analysis over registry + packages + tools + GitHub.

Runs whatever enrichment is present and reports which sources were missing, so
it is useful after a partial pipeline run.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import pandas as pd  # noqa: E402

from mcpstudy import analysis, config, registry  # noqa: E402


def read_jsonl(path):
    if not os.path.isfile(path):
        return None
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    return pd.DataFrame(rows) if rows else None


def save(frame, name):
    path = os.path.join(config.TABLES_DIR, name)
    frame.to_csv(path, index=False, encoding="utf-8")
    print("  table  %-42s %5d rows" % (name, len(frame)))


def main():
    config.load()
    cfg = config.load()
    print("loading sources ...")
    entries = registry.load_entries()
    versions = pd.DataFrame(registry.flatten(entries))
    latest = pd.DataFrame(registry.latest_versions(versions.to_dict("records")))
    latest = analysis.attach_version_counts(versions, latest)
    print("  registry      : %d versions / %d servers" % (len(versions), len(latest)))

    tools = read_jsonl(config.out("tools.jsonl"))
    coverage = read_jsonl(config.out("tool_extraction_coverage.jsonl"))
    enrichment = read_jsonl(config.out("package_enrichment.jsonl"))
    repos = read_jsonl(config.out("github_repos.jsonl"))
    for label, frame in [("tools", tools), ("package enrichment", enrichment),
                         ("github repos", repos)]:
        print("  %-14s: %s" % (label, "absent (run the earlier step)" if frame is None
                               else "%d rows" % len(frame)))

    print("\nconcentration")
    concentration, _ = analysis.version_churn_concentration(versions)
    save(concentration, "t20_version_churn_concentration.csv")

    print("\ninterface design (RQ1)")
    if tools is not None and not tools.empty:
        summary, per_server = analysis.tool_interface_profile(tools)
        save(summary, "t21_tool_interface_summary.csv")
        save(per_server, "t22_tools_per_server.csv")
        if coverage is not None and not coverage.empty:
            ok = coverage[coverage["status"] == "ok"]
            report = pd.DataFrame(
                [
                    ("packages attempted", len(coverage)),
                    ("packages parsed successfully", len(ok)),
                    ("packages yielding >= 1 tool",
                     int((ok["tools_found"].fillna(0) > 0).sum()) if len(ok) else 0),
                ],
                columns=["metric", "value"],
            )
            report["share_of_attempted_pct"] = (
                100.0 * report["value"] / max(1, len(coverage))
            ).round(1)
            save(report, "t23_tool_extraction_coverage.csv")
    else:
        print("  skipped: no extracted tools yet")

    print("\npackage quality")
    if enrichment is not None and not enrichment.empty:
        summary, licences = analysis.package_profile(enrichment)
        save(summary, "t24_package_profile.csv")
        save(licences, "t25_licence_distribution.csv")
    else:
        print("  skipped: no package enrichment yet")

    print("\nrepository health")
    if repos is not None and not repos.empty:
        summary, by_language = analysis.github_profile(repos)
        save(summary, "t26_repository_profile.csv")
        save(by_language, "t27_repositories_by_language.csv")
    else:
        print("  skipped: no GitHub enrichment yet")

    print("\ncross-source")
    save(analysis.cross_source_signals(versions, latest),
         "t28_manifest_properties_vs_activity.csv")

    print("\ndone — results/tables updated")


if __name__ == "__main__":
    main()
