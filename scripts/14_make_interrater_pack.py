"""Step 14 — build a self-contained inter-rater pack.

The first inter-rater round produced near-zero kappa across every field. The
pattern in the second coder's answers (scope_breadth 25/25 `unclear`,
secret_documented_as_secret 25/25 `n/a`, desc_states_inputs 25/25 `n/a`) shows
the coder had no evidence to judge from: the subset file carried only an
item id and a target name.

This script fixes the handoff. It produces one file the second coder can work
from alone, containing, for each of the 50 shared items:
  * the evidence the primary coder used, reproduced verbatim,
  * the blank code columns,
  * the coding rules needed for that item.

Output: results/validation/interrater_pack.md
        results/validation/interrater_worksheet.csv
"""
import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import pandas as pd  # noqa: E402

from mcpstudy import config, registry  # noqa: E402

OUT_DIR = os.path.join(config.RESULTS_DIR, "validation")

PART_B_RULES = """\
allowed values
  auth_mechanism              none | api_key | oauth | bearer_token | basic | jwt |
                              hmac | env_var | browser_session | x402 | prepaid_credit |
                              other | undetermined
  auth_evidence               manifest_env_vars | manifest_description | readme |
                              source | website | no_statement | local_configuration
  requires_user_secret        yes | no | undetermined
  secret_documented_as_secret yes | no | undetermined
  scope_breadth               read_only | narrow | moderate | broad | undetermined
  destructive_capability      yes | no | undetermined
  write_capability            yes | no | undetermined
  readme_warns_about_risk     yes | no | undetermined

two rules that changed after round 1
  1. Use `undetermined` when the evidence does not settle it. Never use `no`
     as a default for missing evidence, and never use `n/a`: it was read two
     different ways in round 1, so it is gone.
  2. `n/a` survives only where the field is structurally impossible. If the
     tool takes no inputs, desc_states_inputs is `n/a`; nothing else uses it.

thresholds for scope_breadth
  read_only     every tool only reads; nothing can be changed, sent or spent
  narrow        writes only to the user's own workspace or a single named item
  moderate      writes to one third-party system the user explicitly connected
  broad         can act on many third-party systems, or on other people
  undetermined  the evidence does not say"""

PART_C_RULES = """\
allowed values
  desc_states_purpose         yes | partial | no
  desc_states_when_to_use     yes | no
  desc_states_inputs          yes | no | n/a
  desc_names_side_effects     yes | no | n/a
  ambiguous_with              a sibling tool name, several separated by |, or empty

definition of each judgement
  purpose          yes = says what it does; partial = names the object only;
                   no = does not say
  when_to_use      yes only if the text tells the agent when to pick this tool
                   over the alternatives. "Use this to X" alone is not enough;
                   it must give a condition, a trigger, or an ordering rule.
  inputs           yes if the parameters are explained in the description,
                   n/a if the tool takes no inputs
  side_effects     yes if it warns about writes, deletions, spending or sending,
                   n/a if the tool is purely read-only by construction
  ambiguous_with   name any sibling from the list below that an agent could
                   plausibly confuse this tool with"""


def read_codes(path):
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return {r["item_id"]: r for r in csv.DictReader(fh)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20260926)
    args = parser.parse_args()

    config.load()
    subset_path = os.path.join(OUT_DIR, "interrater_subset.csv")
    with open(subset_path, encoding="utf-8") as fh:
        subset = list(csv.DictReader(fh))
    b_ids = [r["item_id"] for r in subset if r["part"] == "B"]
    c_ids = [r["item_id"] for r in subset if r["part"] == "C"]

    part_b = read_codes(os.path.join(OUT_DIR, "part_b_codes.csv"))
    part_c = read_codes(os.path.join(OUT_DIR, "part_c_codes.csv"))

    # Evidence for Part B comes from the registry manifest.
    entries = registry.load_entries()
    versions = pd.DataFrame(registry.flatten(entries))
    latest = pd.DataFrame(registry.latest_versions(versions.to_dict("records")))
    latest = latest.set_index("name")
    env_vars = pd.DataFrame(registry.extract_environment_variables(entries))
    env_latest = env_vars[env_vars["is_latest"]] if not env_vars.empty else env_vars

    # Evidence for Part C comes from the extracted tool set.
    tools = pd.read_json(config.out("tools.jsonl"), lines=True)
    siblings = tools.groupby("server_name")["tool_name"].apply(list).to_dict()

    lines = []
    lines.append("# Inter-rater pack (round 2)\n")
    lines.append("You are coding the same 50 items as before. This pack contains the")
    lines.append("evidence for each one, which the previous pack was missing.\n")
    lines.append("Fill `interrater_worksheet.csv`. Do not look at anyone else's codes.\n")

    lines.append("\n---\n\n## Part B rules\n\n```\n%s\n```\n" % PART_B_RULES)
    lines.append("\n## Part C rules\n\n```\n%s\n```\n" % PART_C_RULES)

    lines.append("\n---\n\n# Part B items\n")
    for item_id in b_ids:
        row = part_b.get(item_id)
        if not row:
            continue
        name = row["server_name"]
        lines.append("\n## %s — %s\n" % (item_id, name))
        if name in latest.index:
            manifest = latest.loc[name]
            lines.append("| manifest field | value |")
            lines.append("| --- | --- |")
            lines.append("| title | %s |" % (manifest.get("title") or "(none)"))
            lines.append("| description | %s |"
                         % str(manifest.get("description") or "").replace("|", "\\|"))
            lines.append("| transport | %s |" % (manifest.get("transports") or "(none)"))
            lines.append("| packages | %s |" % (manifest.get("registry_types") or "(none)"))
            lines.append("| repository | %s |" % (manifest.get("repository_url") or "(none)"))
            lines.append("| website | %s |" % (manifest.get("website_url") or "(none)"))
            declared = env_latest[env_latest["server_name"] == name]
            lines.append("| declared env vars | %d |" % len(declared))
            if len(declared):
                lines.append("")
                lines.append("| variable | required | flagged secret |")
                lines.append("| --- | --- | --- |")
                for _, var in declared.iterrows():
                    lines.append("| %s | %s | %s |"
                                 % (var["var_name"], bool(var["is_required"]),
                                    bool(var["is_secret"])))
        else:
            lines.append("_(no manifest row found)_")
        lines.append("\nCodes to assign: auth_mechanism, auth_evidence,")
        lines.append("requires_user_secret, secret_documented_as_secret,")
        lines.append("scope_breadth, destructive_capability, write_capability,")
        lines.append("readme_warns_about_risk.\n")

    lines.append("\n---\n\n# Part C items\n")
    for item_id in c_ids:
        row = part_c.get(item_id)
        if not row:
            continue
        lines.append("\n## %s — %s\n" % (item_id, row["tool_name"]))
        lines.append("Server: `%s`  Language: %s\n" % (row["server_name"], row["language"]))
        match = tools[(tools["server_name"] == row["server_name"])
                      & (tools["tool_name"] == row["tool_name"])]
        description = match.iloc[0]["tool_description"] if len(match) else ""
        lines.append("**Description (verbatim):**\n")
        lines.append("> %s\n" % (description or "(empty)"))
        if len(str(description)) >= 890:
            lines.append("_(this description hit the 900-character extraction cap)_\n")
        sibs = [s for s in siblings.get(row["server_name"], [])
                if s != row["tool_name"]]
        lines.append("\n**Sibling tools (%d):** %s\n"
                     % (len(sibs), ", ".join(sibs[:25]) or "(none)"))
        lines.append("\nCodes to assign: desc_states_purpose, desc_states_when_to_use,")
        lines.append("desc_states_inputs, desc_names_side_effects, ambiguous_with.\n")

    pack_path = os.path.join(OUT_DIR, "interrater_pack.md")
    with open(pack_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    columns = ["item_id", "part", "target",
               "auth_mechanism", "auth_evidence", "requires_user_secret",
               "secret_documented_as_secret", "scope_breadth",
               "destructive_capability", "write_capability",
               "readme_warns_about_risk",
               "desc_states_purpose", "desc_states_when_to_use",
               "desc_states_inputs", "desc_names_side_effects",
               "ambiguous_with", "codebook_version", "notes"]
    ws_path = os.path.join(OUT_DIR, "interrater_worksheet.csv")
    with open(ws_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        for row in subset:
            writer.writerow({
                "item_id": row["item_id"],
                "part": row["part"],
                "target": row["target"],
                "codebook_version": "v1.1",
            })

    print("wrote %s  (%d bytes)" % (pack_path, os.path.getsize(pack_path)))
    print("wrote %s  (%d items)" % (ws_path, len(subset)))
    print("  Part B items: %d   Part C items: %d" % (len(b_ids), len(c_ids)))


if __name__ == "__main__":
    main()
