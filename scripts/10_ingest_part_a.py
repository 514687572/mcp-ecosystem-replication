"""Step 10 — ingest the human Part A codes and recompute extraction quality.

Input  : the coded worksheet returned by the human coder (default path below)
Output : results/validation/part_a_merged.csv     per-package, joined with automation
         results/validation/part_a_summary.csv    the numbers to quote in the paper
         results/validation/part_a_miss_reasons.csv

The human coder was asked for four columns; everything else is joined back in
from results/validation/coding_worksheet.csv so the automated and human views
stay separable and auditable.

Recall and precision are estimated from per-package counts, because the coder
recorded counts rather than tool identities:
    matched   = min(actual, extracted)
    recall    = sum(matched) / sum(actual)
    precision = sum(matched) / sum(extracted)
Both are stated as estimates in the paper, with the tool-identity caveat
recorded in threats to validity.

Run:
  python scripts/10_ingest_part_a.py --codes "<path to coded csv>"
"""
import argparse
import csv
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from mcpstudy import config  # noqa: E402

OUT_DIR = os.path.join(config.RESULTS_DIR, "validation")

# Human vocabulary -> codebook vocabulary. Anything unmapped is kept verbatim
# and surfaced in the output rather than silently coerced.
MISS_REASON_MAP = {
    "": "none",
    "none": "none",
    "no_tools_or_entrypoint_detected": "not_a_server_or_no_tools",
    "no_tools_detected": "no_tools_detected",
    "metadata_error": "other",
    "status_error": "other",
    "extraction_missed_known_server": "other",
}

REGEX_ARTEFACT_PATTERN = re.compile(r"regex.*(误报|多抽|non-?tool|not_a_tool)", re.IGNORECASE)
MISS_PATTERN = re.compile(r"(漏|missed|AST-only|未捕获)", re.IGNORECASE)


def normalize_bool(value):
    text = (value or "").strip().lower()
    if text in ("true", "yes", "y", "1"):
        return True
    if text in ("false", "no", "n", "0"):
        return False
    return None


def to_int(value):
    text = (value or "").strip()
    if text == "":
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def classify_miss(raw, notes, is_server):
    """Map the coder's free-form reason onto the codebook taxonomy."""
    raw = (raw or "").strip()
    notes = (notes or "")
    if not is_server:
        return "not_a_server_or_no_tools", raw
    if REGEX_ARTEFACT_PATTERN.search(raw) or "非工具" in notes:
        return "false_positive", raw
    if MISS_PATTERN.search(raw):
        if "动态" in raw or "dynamic" in raw.lower():
            return "dynamic_registration", raw
        return "extractor_miss", raw
    if raw == "":
        return "none", raw
    return MISS_REASON_MAP.get(raw, raw), raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codes", required=True,
                        help="path to the coded CSV returned by the coder")
    args = parser.parse_args()

    config.load()
    os.makedirs(OUT_DIR, exist_ok=True)

    base_path = os.path.join(OUT_DIR, "coding_worksheet.csv")
    with open(base_path, encoding="utf-8") as fh:
        base = {row["pkg_key"]: row for row in csv.DictReader(fh)}

    with open(args.codes, encoding="utf-8") as fh:
        coded = list(csv.DictReader(fh))

    missing = [r["pkg_key"] for r in coded if r["pkg_key"] not in base]
    if missing:
        print("warning: %d coded keys not found in the worksheet" % len(missing))

    merged = []
    for row in coded:
        key = row["pkg_key"]
        original = base.get(key, {})
        is_server = normalize_bool(row.get("has_server_entrypoint"))
        actual = to_int(row.get("n_tools_actual"))
        extracted = to_int(original.get("n_tools_extracted"))
        if extracted is None:
            extracted = 0
        if actual is None:
            actual = 0
        if not is_server:
            actual = 0
        matched = min(actual, extracted) if is_server else 0
        taxonomy, raw_reason = classify_miss(
            row.get("miss_reason"), row.get("notes"), bool(is_server)
        )
        merged.append(
            {
                "pkg_key": key,
                "registry_type": original.get("registry_type"),
                "has_server_entrypoint": is_server,
                "n_tools_actual": actual,
                "n_tools_extracted": extracted,
                "matched": matched,
                "under_extracted": max(0, actual - extracted),
                "over_extracted": max(0, extracted - actual),
                "miss_reason_taxonomy": taxonomy,
                "miss_reason_raw": raw_reason,
                "notes": row.get("notes", ""),
            }
        )

    merged_path = os.path.join(OUT_DIR, "part_a_merged.csv")
    with open(merged_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(merged[0].keys()))
        writer.writeheader()
        writer.writerows(merged)

    servers = [r for r in merged if r["has_server_entrypoint"]]
    not_servers = [r for r in merged if not r["has_server_entrypoint"]]
    detected = [r for r in servers if r["n_tools_extracted"] > 0]
    total_actual = sum(r["n_tools_actual"] for r in servers)
    total_extracted = sum(r["n_tools_extracted"] for r in servers)
    total_matched = sum(r["matched"] for r in servers)
    missed = sum(r["under_extracted"] for r in servers)
    extra = sum(r["over_extracted"] for r in servers)

    def pct(part, whole):
        return round(100.0 * part / whole, 1) if whole else 0.0

    summary = [
        ("coded packages", len(merged)),
        ("coder classified as an MCP server", len(servers)),
        ("coder classified as not a server", len(not_servers)),
        ("servers where the extractor found >= 1 tool", len(detected)),
        ("package-level detection rate (%)", pct(len(detected), len(servers))),
        ("tools actually exposed (coder count)", total_actual),
        ("tools extracted by the pipeline", total_extracted),
        ("tools matched (estimated)", total_matched),
        ("tools missed by the extractor", missed),
        ("tools extracted that are not real tools", extra),
        ("estimated tool-level recall (%)", pct(total_matched, total_actual)),
        ("estimated tool-level precision (%)", pct(total_matched, total_extracted)),
        ("servers with at least one miss", sum(1 for r in servers
                                               if r["under_extracted"] > 0)),
    ]
    summary_path = os.path.join(OUT_DIR, "part_a_summary.csv")
    with open(summary_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["metric", "value"])
        writer.writerows(summary)

    reasons = {}
    for record in merged:
        reasons[record["miss_reason_taxonomy"]] = (
            reasons.get(record["miss_reason_taxonomy"], 0) + 1
        )
    reasons_path = os.path.join(OUT_DIR, "part_a_miss_reasons.csv")
    with open(reasons_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["miss_reason_taxonomy", "packages"])
        for name, count in sorted(reasons.items(), key=lambda kv: -kv[1]):
            writer.writerow([name, count])

    for metric, value in summary:
        print("  %-46s %s" % (metric, value))
    print("\nmiss reasons:")
    for name, count in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print("  %-32s %d" % (name, count))
    print("\nwrote results/validation/part_a_{merged,summary,miss_reasons}.csv")


if __name__ == "__main__":
    main()
