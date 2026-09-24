"""Step 12 — ingest the human Part C (tool description quality) codes.

Input : the coded worksheet returned by the coder (results/validation/t3.txt),
        which arrives wrapped in a ```csv fence.
Output: results/validation/part_c_codes.csv       normalised copy
        results/validation/part_c_summary.csv     headline metrics for RQ1
        results/validation/part_c_crosstabs.csv   per-code distributions
        results/validation/part_c_by_language.csv
        results/validation/part_c_ambiguity.csv   tools with ambiguous siblings
"""
import argparse
import csv
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from mcpstudy import config  # noqa: E402

OUT_DIR = os.path.join(config.RESULTS_DIR, "validation")


def load_codes(path):
    """Read a CSV that may be wrapped in a Markdown code fence."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    lines = [line for line in text.splitlines()
             if not line.strip().startswith("```")]
    while lines and not lines[0].strip():
        lines.pop(0)
    return list(csv.DictReader(io.StringIO("\n".join(lines))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codes", default=os.path.join(OUT_DIR, "t3.txt"))
    args = parser.parse_args()

    config.load()
    rows = load_codes(args.codes)

    normalised = []
    for row in rows:
        row = {k: (v or "").strip() for k, v in row.items()}
        if not row.get("item_id"):
            continue
        normalised.append({
            "item_id": row["item_id"],
            "server_name": row["server_name"],
            "language": row["language"],
            "tool_name": row["tool_name"],
            "desc_states_purpose": row["desc_states_purpose"],
            "desc_states_when_to_use": row["desc_states_when_to_use"],
            "desc_states_inputs": row["desc_states_inputs"],
            "desc_names_side_effects": row["desc_names_side_effects"],
            "ambiguous_with": row["ambiguous_with"],
            "ambiguous_count": len([x for x in row["ambiguous_with"].split("|")
                                    if x.strip()]),
            "notes": row.get("notes", ""),
        })

    codes_path = os.path.join(OUT_DIR, "part_c_codes.csv")
    with open(codes_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(normalised[0].keys()))
        writer.writeheader()
        writer.writerows(normalised)

    total = len(normalised)

    def pct(n):
        return round(100.0 * n / total, 1) if total else 0.0

    def count(predicate):
        return sum(1 for r in normalised if predicate(r))

    purpose_yes = count(lambda r: r["desc_states_purpose"] == "yes")
    purpose_partial = count(lambda r: r["desc_states_purpose"] == "partial")
    when_yes = count(lambda r: r["desc_states_when_to_use"] == "yes")
    inputs_yes = count(lambda r: r["desc_states_inputs"] == "yes")
    effects_yes = count(lambda r: r["desc_names_side_effects"] == "yes")
    ambiguous = count(lambda r: r["ambiguous_count"] > 0)
    purpose_missing = count(lambda r: r["desc_states_purpose"] == "no")

    summary = [
        ("tools coded", total),
        ("description states the purpose (yes)", purpose_yes),
        ("description states the purpose (partial)", purpose_partial),
        ("description does NOT state the purpose", purpose_missing),
        ("description states WHEN to use the tool", when_yes),
        ("... as a share of coded tools (%)", pct(when_yes)),
        ("description explains the inputs", inputs_yes),
        ("... as a share (%)", pct(inputs_yes)),
        ("description names side effects", effects_yes),
        ("tools the coder found ambiguous with a sibling", ambiguous),
        ("... as a share (%)", pct(ambiguous)),
        ("mean ambiguous siblings per tool",
         round(sum(r["ambiguous_count"] for r in normalised) / max(1, total), 2)),
        ("tools that state purpose AND when to use",
         count(lambda r: r["desc_states_purpose"] == "yes"
               and r["desc_states_when_to_use"] == "yes")),
    ]
    summary_path = os.path.join(OUT_DIR, "part_c_summary.csv")
    with open(summary_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["metric", "value"])
        writer.writerows(summary)

    crosstabs = []
    for column in ("desc_states_purpose", "desc_states_when_to_use",
                   "desc_states_inputs", "desc_names_side_effects", "language"):
        values = sorted({r[column] for r in normalised})
        for value in values:
            n = count(lambda r, v=value, c=column: r[c] == v)
            crosstabs.append({"field": column, "value": value,
                              "tools": n, "share_pct": pct(n)})
    crosstab_path = os.path.join(OUT_DIR, "part_c_crosstabs.csv")
    with open(crosstab_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["field", "value", "tools", "share_pct"])
        writer.writeheader()
        writer.writerows(crosstabs)

    by_language = []
    for language in sorted({r["language"] for r in normalised}):
        subset = [r for r in normalised if r["language"] == language]
        n = len(subset)
        by_language.append({
            "language": language,
            "tools": n,
            "share_pct": pct(n),
            "purpose_yes_pct": round(
                100.0 * sum(1 for r in subset
                            if r["desc_states_purpose"] == "yes") / n, 1),
            "when_to_use_pct": round(
                100.0 * sum(1 for r in subset
                            if r["desc_states_when_to_use"] == "yes") / n, 1),
            "inputs_explained_pct": round(
                100.0 * sum(1 for r in subset
                            if r["desc_states_inputs"] == "yes") / n, 1),
            "ambiguous_pct": round(
                100.0 * sum(1 for r in subset
                            if r["ambiguous_count"] > 0) / n, 1),
        })
    language_path = os.path.join(OUT_DIR, "part_c_by_language.csv")
    with open(language_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(by_language[0].keys()))
        writer.writeheader()
        writer.writerows(by_language)

    ambiguity_path = os.path.join(OUT_DIR, "part_c_ambiguity.csv")
    with open(ambiguity_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["item_id", "server_name", "tool_name",
                            "ambiguous_count", "ambiguous_with", "notes"]
        )
        writer.writeheader()
        for row in normalised:
            if row["ambiguous_count"] > 0:
                writer.writerow({k: row[k] for k in writer.fieldnames})

    for metric, value in summary:
        print("  %-56s %s" % (metric, value))
    print("\nby language:")
    for row in by_language:
        print("  %-22s n=%-4d purpose=%-5.1f%% when=%-5.1f%% inputs=%-5.1f%% ambiguous=%.1f%%"
              % (row["language"], row["tools"], row["purpose_yes_pct"],
                 row["when_to_use_pct"], row["inputs_explained_pct"],
                 row["ambiguous_pct"]))
    print("\nwrote results/validation/part_c_{codes,summary,crosstabs,by_language,ambiguity}.csv")


if __name__ == "__main__":
    main()
