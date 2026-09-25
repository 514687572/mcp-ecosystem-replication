"""Step 2 — build the registry census tables and figures.

Reads data/raw/registry.jsonl and writes:
  results/tables/*.csv      the tables reported in the paper
  results/figures/*.png     the figures reported in the paper

Runs on registry data alone, so it works as soon as step 1 has finished.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import pandas as pd  # noqa: E402

from mcpstudy import analysis, config, figures, registry  # noqa: E402


def save(frame, name, notes=""):
    path = os.path.join(config.TABLES_DIR, name)
    frame.to_csv(path, index=False, encoding="utf-8")
    print("  table  %-38s %5d rows" % (name, len(frame)))
    if notes:
        print("         %s" % notes)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args()

    cfg = config.load()
    as_of = cfg["project"]["freeze_window_end"]
    top_n = int(cfg["analysis"]["top_n"])
    min_servers = int(cfg["analysis"]["namespace_min_servers"])

    print("loading registry harvest ...")
    entries = registry.load_entries()
    print("  %d raw entries" % len(entries))

    versions = pd.DataFrame(registry.flatten(entries))
    packages = pd.DataFrame(registry.extract_packages(entries))
    env_vars = pd.DataFrame(registry.extract_environment_variables(entries))
    remotes = pd.DataFrame(registry.extract_remotes(entries))

    latest = pd.DataFrame(registry.latest_versions(versions.to_dict("records")))
    latest = analysis.attach_version_counts(versions, latest)

    versions.to_csv(config.out("registry_versions.csv"), index=False, encoding="utf-8")
    latest.to_csv(config.out("registry_latest.csv"), index=False, encoding="utf-8")
    print("  %d published versions across %d distinct server names"
          % (len(versions), len(latest)))

    print("\ncensus")
    save(analysis.census_overview(versions, latest), "t01_census_overview.csv")
    save(analysis.field_completeness(latest), "t02_field_completeness.csv")

    top, all_ns = analysis.namespace_concentration(latest, top_n, min_servers)
    save(top, "t03_top_publishers.csv")
    save(all_ns, "t03b_all_namespaces.csv")
    recurring = all_ns[all_ns["recurring"]]
    print("         %d namespaces publish >= %d servers (%.1f%% of all servers)"
          % (len(recurring), min_servers,
             100.0 * recurring["servers"].sum() / max(1, len(latest))))

    save(analysis.transport_distribution(versions), "t04_transports.csv")
    save(analysis.registry_type_distribution(packages), "t05_package_registries.csv")
    save(analysis.schema_adoption(versions), "t06_schema_adoption.csv")

    timeline = analysis.publishing_timeline(versions)
    save(timeline, "t07_publishing_timeline.csv")

    save(analysis.version_distribution(latest), "t08_versions_per_server.csv")
    desc_summary, desc_stats, desc_frame = analysis.description_quality(latest)
    save(desc_summary, "t09_description_issues.csv")
    save(desc_stats, "t09b_description_stats.csv")

    naming, naming_frame = analysis.naming_conventions(latest)
    save(naming, "t10_naming_conventions.csv")

    print("\nsecurity")
    (cred_summary, top_vars, cred_audit, cred_precision,
     cred_decomposition) = analysis.credential_declarations(env_vars)
    if not cred_summary.empty:
        save(cred_summary, "t11_credential_hygiene.csv")
        save(top_vars, "t12_most_common_env_vars.csv")
        save(cred_audit, "t11b_credential_rule_audit.csv")
        save(cred_precision, "t11c_credential_rule_precision.csv")
        save(cred_decomposition, "t11d_permissive_rule_decomposition.csv")
    remote_summary, top_hosts = analysis.remote_endpoint_hygiene(remotes)
    if not remote_summary.empty:
        save(remote_summary, "t13_remote_endpoint_hygiene.csv")
        save(top_hosts, "t14_top_remote_hosts.csv")

    print("\nevolution")
    save(analysis.release_cadence(versions), "t15_release_cadence.csv")
    stale, stale_frame = analysis.staleness(latest, as_of)
    save(stale, "t16_staleness.csv")
    save(analysis.deprecations(latest), "t17_deprecated_servers.csv")

    if not args.no_figures:
        print("\nfigures")
        figures.make_all(timeline, latest, env_vars, remotes, figures_dir=config.FIGURES_DIR)

    print("\ndone — tables in results/tables/, figures in results/figures/")


if __name__ == "__main__":
    main()
