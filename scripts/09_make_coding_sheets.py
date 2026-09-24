"""Step 9 — build the human coding sheets for codebook parts B and C.

Part A (tool-extraction validation) is produced by script 08. Parts B and C
need a person, so this script produces the tables they fill in, together with
the evidence needed to fill them quickly:

  results/validation/part_b_security_worksheet.csv   150 servers, blank codes
  results/validation/part_b_evidence.txt             per-server manifest facts
  results/validation/part_c_tool_worksheet.csv       200 tools, blank codes
  results/validation/part_c_evidence.txt             full descriptions + siblings
  results/validation/interrater_subset.csv           50 items for a second coder

Sampling is stratified and seeded, so the analysed set is reproducible from the
frozen registry snapshot.

Run: python scripts/09_make_coding_sheets.py --seed 20260926
"""
import argparse
import csv
import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import pandas as pd  # noqa: E402

from mcpstudy import config, registry  # noqa: E402

OUT_DIR = os.path.join(config.RESULTS_DIR, "validation")

PART_B_COLUMNS = [
    "item_id",
    "server_name",
    "transport_class",
    "auth_mechanism",
    "auth_evidence",
    "requires_user_secret",
    "secret_documented_as_secret",
    "scope_breadth",
    "destructive_capability",
    "write_capability",
    "readme_warns_about_risk",
    "notes",
]

PART_C_COLUMNS = [
    "item_id",
    "server_name",
    "language",
    "tool_name",
    "desc_states_purpose",
    "desc_states_when_to_use",
    "desc_states_inputs",
    "desc_names_side_effects",
    "ambiguous_with",
    "notes",
]


def transport_class(row):
    has_pkg = bool(row.get("has_packages"))
    has_remote = bool(row.get("has_remotes"))
    if has_pkg and has_remote:
        return "package+remote"
    if has_pkg:
        return "package-only"
    if has_remote:
        return "remote-only"
    return "neither"


def stratified_sample(frame, stratum_column, total, rng):
    """Draw `total` rows spread proportionally across strata."""
    groups = list(frame.groupby(stratum_column))
    sizes = {key: len(sub) for key, sub in groups}
    population = sum(sizes.values())
    picked = []
    for key, sub in groups:
        share = sizes[key] / float(population)
        n = max(1, int(round(share * total)))
        n = min(n, len(sub))
        picked.extend(rng.sample(list(sub.index), n))
    if len(picked) > total:
        picked = rng.sample(picked, total)
    elif len(picked) < total:
        remaining = [i for i in frame.index if i not in set(picked)]
        picked.extend(rng.sample(remaining, min(total - len(picked), len(remaining))))
    return picked


def write_csv(path, columns, rows):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--part-b", type=int, default=150)
    parser.add_argument("--part-c", type=int, default=200)
    parser.add_argument("--interrater", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20260926)
    args = parser.parse_args()

    config.load()
    os.makedirs(OUT_DIR, exist_ok=True)

    entries = registry.load_entries()
    latest = pd.DataFrame(registry.latest_versions(
        pd.DataFrame(registry.flatten(entries)).to_dict("records")
    ))
    latest["transport_class"] = [transport_class(r) for _, r in latest.iterrows()]
    latest = latest.sort_values("name").reset_index(drop=True)
    env_vars = pd.DataFrame(registry.extract_environment_variables(entries))

    rng = random.Random(args.seed)

    # ---- Part B -------------------------------------------------------------
    seed_env = (
        env_vars[env_vars["is_latest"]]
        .groupby("server_name")
        .agg(env_vars=("var_name", "size"),
             secrets_declared=("is_secret", "sum"),
             required=("is_required", "sum"))
        .reset_index()
    )
    b_frame = latest.merge(seed_env, left_on="name", right_on="server_name",
                           how="left")
    picked = stratified_sample(b_frame, "transport_class", args.part_b, rng)
    b_sample = b_frame.loc[picked].sort_values("name").reset_index(drop=True)

    b_rows = []
    for index, row in b_sample.iterrows():
        b_rows.append({
            "item_id": "B%03d" % (index + 1),
            "server_name": row["name"],
            "transport_class": row["transport_class"],
            "auth_mechanism": "", "auth_evidence": "",
            "requires_user_secret": "", "secret_documented_as_secret": "",
            "scope_breadth": "", "destructive_capability": "",
            "write_capability": "", "readme_warns_about_risk": "", "notes": "",
        })
    write_csv(os.path.join(OUT_DIR, "part_b_security_worksheet.csv"),
              PART_B_COLUMNS, b_rows)

    with open(os.path.join(OUT_DIR, "part_b_evidence.txt"), "w",
              encoding="utf-8") as fh:
        fh.write("PART B EVIDENCE PACK\n")
        fh.write("For each server: everything the registry declares, plus the\n")
        fh.write("links you need to judge authentication and scope.\n")
        fh.write("Do NOT probe live endpoints. Use the repository README and source.\n")
        for index, row in b_sample.iterrows():
            fh.write("\n" + "=" * 78 + "\n")
            fh.write("%s  %s\n" % ("B%03d" % (index + 1), row["name"]))
            fh.write("  title         : %s\n" % (row.get("title") or "(none)"))
            fh.write("  description   : %s\n" % (row.get("description") or ""))
            fh.write("  version       : %s\n" % row.get("version"))
            fh.write("  transport     : %s   [%s]\n"
                     % (row.get("transports") or "(none)", row["transport_class"]))
            fh.write("  packages      : %s\n" % (row.get("registry_types") or "(none)"))
            fh.write("  repository    : %s\n" % (row.get("repository_url") or "(none)"))
            fh.write("  website       : %s\n" % (row.get("website_url") or "(none)"))
            fh.write("  env vars      : %s declared, %s flagged secret, %s required\n"
                     % (int(row["env_vars"]) if pd.notna(row["env_vars"]) else 0,
                        int(row["secrets_declared"])
                        if pd.notna(row["secrets_declared"]) else 0,
                        int(row["required"]) if pd.notna(row["required"]) else 0))

    # ---- Part C -------------------------------------------------------------
    tools_path = config.out("tools.jsonl")
    if not os.path.isfile(tools_path):
        print("no tools.jsonl yet — run scripts/04_extract_tools.py first")
        return
    tools = pd.read_json(tools_path, lines=True)
    tools = tools[tools["language"].isin(["python", "javascript"])].copy()
    tools["language_bucket"] = tools["language"].replace(
        {"javascript": "javascript/typescript"}
    )
    tools = tools.sort_values(["server_name", "tool_name"]).reset_index(drop=True)
    picked_c = stratified_sample(tools, "language_bucket", args.part_c, rng)
    c_sample = tools.loc[picked_c].sort_values(
        ["language_bucket", "server_name", "tool_name"]
    ).reset_index(drop=True)

    c_rows = []
    for index, row in c_sample.iterrows():
        c_rows.append({
            "item_id": "C%03d" % (index + 1),
            "server_name": row["server_name"],
            "language": row["language_bucket"],
            "tool_name": row["tool_name"],
            "desc_states_purpose": "", "desc_states_when_to_use": "",
            "desc_states_inputs": "", "desc_names_side_effects": "",
            "ambiguous_with": "", "notes": "",
        })
    write_csv(os.path.join(OUT_DIR, "part_c_tool_worksheet.csv"),
              PART_C_COLUMNS, c_rows)

    siblings = tools.groupby("server_name")["tool_name"].apply(list).to_dict()
    with open(os.path.join(OUT_DIR, "part_c_evidence.txt"), "w",
              encoding="utf-8") as fh:
        fh.write("PART C EVIDENCE PACK\n")
        fh.write("The full description is reproduced verbatim. Sibling tools are\n")
        fh.write("listed because `ambiguous_with` is judged against them.\n")
        for index, row in c_sample.iterrows():
            fh.write("\n" + "=" * 78 + "\n")
            fh.write("%s  %s   (%s)\n"
                     % ("C%03d" % (index + 1), row["tool_name"], row["language_bucket"]))
            fh.write("  server      : %s\n" % row["server_name"])
            fh.write("  package     : %s\n" % row.get("package_key"))
            fh.write("  description : %s\n"
                     % (row.get("tool_description") or "(empty)"))
            if len(str(row.get("tool_description") or "")) >= 890:
                fh.write("  !! description hit the 900-character extraction cap;"
                         " consult the package source if the ending matters\n")
            fh.write("  schema seen : %s\n" % bool(row.get("has_schema")))
            sibs = [s for s in siblings.get(row["server_name"], [])
                    if s != row["tool_name"]]
            fh.write("  sibling tools (%d): %s\n"
                     % (len(sibs), ", ".join(sibs[:20]) or "(none)"))

    # ---- inter-rater subset -------------------------------------------------
    subset_rows = []
    half = args.interrater // 2
    for row in b_rows[:half]:
        subset_rows.append({"item_id": row["item_id"], "part": "B",
                            "target": row["server_name"]})
    for row in c_rows[: args.interrater - half]:
        subset_rows.append({"item_id": row["item_id"], "part": "C",
                            "target": "%s :: %s"
                                      % (row["server_name"], row["tool_name"])})
    write_csv(os.path.join(OUT_DIR, "interrater_subset.csv"),
              ["item_id", "part", "target"], subset_rows)

    print("Part B : %d servers -> part_b_security_worksheet.csv"
          % len(b_rows))
    print("         transport strata: %s"
          % b_sample["transport_class"].value_counts().to_dict())
    print("Part C : %d tools -> part_c_tool_worksheet.csv" % len(c_rows))
    print("         language strata: %s"
          % c_sample["language_bucket"].value_counts().to_dict())
    print("inter-rater subset: %d items -> interrater_subset.csv"
          % len(subset_rows))
    print("seed %d recorded" % args.seed)


if __name__ == "__main__":
    main()
