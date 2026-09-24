"""Step 15 — build the v1.2 inter-rater pack (round 3).

Round 2 fixed the missing-evidence problem and produced usable agreement on
seven of eleven fields. Four still failed, each for a different reason, and
docs/codebook_v1.2.md responds to each:

  desc_names_side_effects       enumeration defect   -> n/a removed
  desc_states_when_to_use       threshold difference -> worked examples added
  secret_documented_as_secret   evidence scope       -> manifest table only
  readme_warns_about_risk       unanswerable         -> field withdrawn

This script emits the round 3 pack. It reads the rules from
docs/codebook_v1.2.md rather than duplicating them, so the codebook stays the
single source of truth.

Output: results/validation/interrater_pack_v1.2.md
        results/validation/interrater_worksheet_v1.2.csv
"""
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import pandas as pd  # noqa: E402

from mcpstudy import config, registry  # noqa: E402

OUT_DIR = os.path.join(config.RESULTS_DIR, "validation")
DOCS_DIR = os.path.join(config.PROJECT_ROOT, "docs")

CODEBOOK_FIELDS_B = [
    "auth_mechanism",
    "auth_evidence",
    "requires_user_secret",
    "secret_documented_as_secret",
    "scope_breadth",
    "destructive_capability",
    "write_capability",
]

CODEBOOK_FIELDS_C = [
    "desc_states_purpose",
    "desc_states_when_to_use",
    "desc_states_inputs",
    "desc_names_side_effects",
    "ambiguous_with",
]

CREDENTIAL_HINTS = (
    "token", "key", "secret", "password", "passwd", "credential",
    "auth", "pat", "cookie", "session", "private", "dsn",
)


def codebook_section(title):
    """Pull a section out of docs/codebook_v1.2.md by heading text."""
    path = os.path.join(DOCS_DIR, "codebook_v1.2.md")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    pattern = re.compile(r"^##+ .*%s.*?$(.*?)(?=^##+ |\Z)" % re.escape(title),
                         re.MULTILINE | re.DOTALL)
    match = pattern.search(text)
    return match.group(1).strip() if match else "(section not found)"


def read_codes(path):
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8-sig") as fh:
        return {r["item_id"]: r for r in csv.DictReader(fh)}


def looks_like_credential(name):
    return any(hint in (name or "").lower() for hint in CREDENTIAL_HINTS)


def manifest_secret_verdict(declared):
    """Apply the v1.2 manifest-only rule for secret_documented_as_secret."""
    if declared is None or len(declared) == 0:
        return "n/a", "no environment variables declared"
    cred = declared[declared["var_name"].fillna("").apply(looks_like_credential)]
    if len(cred) == 0:
        return "n/a", "declares variables, none credential-like"
    if bool(cred["is_secret"].any()):
        return "yes", "at least one credential-like variable flagged secret"
    return "no", "credential-like variable declared but not flagged secret"


def main():
    config.load()
    with open(os.path.join(OUT_DIR, "interrater_subset.csv"), encoding="utf-8-sig") as fh:
        subset = list(csv.DictReader(fh))
    b_ids = [r["item_id"] for r in subset if r["part"] == "B"]
    c_ids = [r["item_id"] for r in subset if r["part"] == "C"]

    part_b = read_codes(os.path.join(OUT_DIR, "part_b_codes.csv"))
    part_c = read_codes(os.path.join(OUT_DIR, "part_c_codes.csv"))

    entries = registry.load_entries()
    latest = pd.DataFrame(registry.latest_versions(
        pd.DataFrame(registry.flatten(entries)).to_dict("records")
    )).set_index("name")
    env_vars = pd.DataFrame(registry.extract_environment_variables(entries))
    env_latest = env_vars[env_vars["is_latest"]] if not env_vars.empty else env_vars

    tools = pd.read_json(config.out("tools.jsonl"), lines=True)
    siblings = tools.groupby("server_name")["tool_name"].apply(list).to_dict()

    lines = []
    lines.append("# Inter-rater pack, round 3 (codebook v1.2)\n")
    lines.append("Same 50 items as round 2, coded again under codebook v1.2.")
    lines.append("Four fields changed; the rest are as in round 2.\n")
    lines.append("Fill `interrater_worksheet_v1.2.csv`. Work independently.\n")
    lines.append("\n---\n\n## What changed and why\n")
    lines.append(codebook_section("What round 2 showed"))
    lines.append("\n## Change 1 — desc_names_side_effects\n")
    lines.append(codebook_section("Change 1"))
    lines.append("\n## Change 2 — desc_states_when_to_use\n")
    lines.append(codebook_section("Change 2"))
    lines.append("\n## Change 3 — secret_documented_as_secret\n")
    lines.append(codebook_section("Change 3"))
    lines.append("\n## Change 4 — readme_warns_about_risk withdrawn\n")
    lines.append(codebook_section("Change 4"))
    lines.append("\n---\n\n# Part B items\n")

    for item_id in b_ids:
        row = part_b.get(item_id)
        if not row:
            continue
        name = row["server_name"]
        lines.append("\n## %s — %s\n" % (item_id, name))
        declared = None
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
            lines.append("")
            lines.append("**Declared environment variables (%d)** — the only evidence"
                         " for secret_documented_as_secret:" % len(declared))
            lines.append("")
            if len(declared):
                lines.append("| variable | required | flagged secret |")
                lines.append("| --- | --- | --- |")
                for _, var in declared.iterrows():
                    lines.append("| %s | %s | %s |"
                                 % (var["var_name"], bool(var["is_required"]),
                                    bool(var["is_secret"])))
            else:
                lines.append("_none declared_")
            verdict, reason = manifest_secret_verdict(declared)
            lines.append("")
            lines.append("> v1.2 manifest rule gives **%s** for this item (%s)."
                         % (verdict.upper(), reason))
            lines.append("> Confirm it yourself from the table above.")
        else:
            lines.append("_(no manifest row found)_")
        lines.append("\nCodes to assign: %s.\n" % ", ".join(CODEBOOK_FIELDS_B))

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
        lines.append("\nCodes to assign: %s.\n" % ", ".join(CODEBOOK_FIELDS_C))

    pack_path = os.path.join(OUT_DIR, "interrater_pack_v1.2.md")
    with open(pack_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    columns = (["item_id", "part", "target"] + CODEBOOK_FIELDS_B
               + CODEBOOK_FIELDS_C + ["codebook_version", "notes"])
    ws_path = os.path.join(OUT_DIR, "interrater_worksheet_v1.2.csv")
    with open(ws_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        for row in subset:
            writer.writerow({"item_id": row["item_id"], "part": row["part"],
                             "target": row["target"], "codebook_version": "v1.2"})

    print("wrote %s (%d bytes)" % (pack_path, os.path.getsize(pack_path)))
    print("wrote %s (%d items)" % (ws_path, len(subset)))
    print("fields: %d Part B + %d Part C = %d"
          % (len(CODEBOOK_FIELDS_B), len(CODEBOOK_FIELDS_C),
             len(CODEBOOK_FIELDS_B) + len(CODEBOOK_FIELDS_C)))
    print("withdrawn: readme_warns_about_risk")


if __name__ == "__main__":
    main()
