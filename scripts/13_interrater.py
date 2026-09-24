"""Step 13 — inter-rater agreement between the primary and second coder.

Inputs : results/validation/part_b_codes.csv   (primary, 150 servers)
         results/validation/part_c_codes.csv   (primary, 200 tools)
         results/validation/第二编码者编码结果.csv (second coder, 50 items)
Output : results/validation/interrater_agreement.csv
         results/validation/interrater_disagreements.csv

Reports Cohen's kappa and observed agreement per field, on the 50-item subset
only. Free-text fields (auth_evidence, notes) are excluded: kappa is not
defined on unbounded text. For `ambiguous_with`, which is a set of tool names,
agreement is computed on the derived binary "has any ambiguous sibling".

Kappa is reported for every field before any aggregate is computed, because a
single pooled number would hide which judgements are reliable.
"""
import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from mcpstudy import config  # noqa: E402

OUT_DIR = os.path.join(config.RESULTS_DIR, "validation")

PART_B_FIELDS = [
    "auth_mechanism",
    "requires_user_secret",
    "secret_documented_as_secret",
    "scope_breadth",
    "destructive_capability",
    "write_capability",
    "readme_warns_about_risk",
]

PART_C_FIELDS = [
    "desc_states_purpose",
    "desc_states_when_to_use",
    "desc_states_inputs",
    "desc_names_side_effects",
]


def cohens_kappa(pairs):
    """Cohen's kappa over (primary, second) label pairs."""
    n = len(pairs)
    if n == 0:
        return None, None, None
    labels = sorted({value for pair in pairs for value in pair})
    observed = sum(1 for a, b in pairs if a == b) / float(n)
    expected = 0.0
    for label in labels:
        p_a = sum(1 for a, _ in pairs if a == label) / float(n)
        p_b = sum(1 for _, b in pairs if b == label) / float(n)
        expected += p_a * p_b
    if expected >= 1.0:
        return observed, expected, None
    return observed, expected, (observed - expected) / (1.0 - expected)


def normalise_ambiguous(value):
    return "yes" if (value or "").strip() else "no"


# Values that all mean "the evidence does not settle this". The codebook offers
# both `unclear` and `n/a`, and the two coders read them differently, so the
# diagnostic pass below collapses them to test whether the disagreement is
# substantive or lexical.
UNDETERMINED = {"", "unclear", "n/a", "na", "n/a ", "unknown"}


def collapse_undetermined(value):
    text = (value or "").strip().lower()
    return "undetermined" if text in {v.strip().lower() for v in UNDETERMINED} else text


def harmonize_primary(value):
    """Map v1.0 vocabulary onto v1.1 without merging genuinely different codes.

    The primary coder worked under codebook v1.0 and the second under v1.1. The
    only difference that is purely lexical is the word for "the evidence does
    not settle this": v1.0 said `unclear`, v1.1 says `undetermined`. Comparing
    the two files raw therefore scores identical judgements as disagreements.

    `n/a` is deliberately NOT merged here. In v1.1 it means "structurally
    impossible" (a input-less tool, a read-only tool), which is a different
    claim from `undetermined`. Merging them would hide a real disagreement.
    """
    text = (value or "").strip()
    return "undetermined" if text.lower() == "unclear" else text


def kappa_band(kappa):
    """Landis & Koch (1977) interpretation of a kappa value."""
    if kappa is None or kappa == "":
        return "not estimable"
    kappa = float(kappa)
    if kappa < 0.0:
        return "poor"
    if kappa < 0.20:
        return "slight"
    if kappa < 0.40:
        return "fair"
    if kappa < 0.60:
        return "moderate"
    if kappa < 0.80:
        return "substantial"
    return "almost perfect"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--second",
                        default=os.path.join(OUT_DIR, "第二编码者编码结果_v1.1.csv"),
                        help="second coder's file; defaults to the v1.1 round")
    args = parser.parse_args()

    config.load()

    # utf-8-sig: the returned files are frequently saved with a BOM, which
    # otherwise turns the first column name into '\ufeffitem_id'.
    with open(os.path.join(OUT_DIR, "part_b_codes.csv"),
              encoding="utf-8-sig") as fh:
        primary_b = {r["item_id"]: r for r in csv.DictReader(fh)}
    with open(os.path.join(OUT_DIR, "part_c_codes.csv"),
              encoding="utf-8-sig") as fh:
        primary_c = {r["item_id"]: r for r in csv.DictReader(fh)}
    with open(args.second, encoding="utf-8-sig") as fh:
        second = list(csv.DictReader(fh))

    results = []
    disagreements = []

    def add_agreement(part, field, pairs, collapse=False):
        use = [(collapse_undetermined(a), collapse_undetermined(b)) if collapse
               else (a, b) for a, b in pairs]
        observed, expected, kappa = cohens_kappa(use)
        return {
            "part": part, "field": field, "items": len(use),
            "observed_agreement": round(observed, 3) if observed is not None else "",
            "expected_agreement": round(expected, 3) if expected is not None else "",
            "cohens_kappa": round(kappa, 3) if kappa is not None else "",
        }

    for field in PART_B_FIELDS:
        pairs = []
        for row in second:
            if row.get("part") != "B":
                continue
            primary = primary_b.get(row["item_id"])
            if not primary:
                continue
            a = (primary.get(field) or "").strip()
            b = (row.get(field) or "").strip()
            pairs.append((a, b))
            if a != b:
                disagreements.append({
                    "part": "B", "item_id": row["item_id"],
                    "target": row.get("target"), "field": field,
                    "primary": a, "second": b,
                })
        results.append(add_agreement("B", field, pairs))

    for field in PART_C_FIELDS:
        pairs = []
        for row in second:
            if row.get("part") != "C":
                continue
            primary = primary_c.get(row["item_id"])
            if not primary:
                continue
            a = (primary.get(field) or "").strip()
            b = (row.get(field) or "").strip()
            pairs.append((a, b))
            if a != b:
                disagreements.append({
                    "part": "C", "item_id": row["item_id"],
                    "target": row.get("target"), "field": field,
                    "primary": a, "second": b,
                })
        results.append(add_agreement("C", field, pairs))

    # ambiguous_with, reduced to a binary because agreement on a set of names
    # is not what kappa measures.
    pairs = []
    for row in second:
        if row.get("part") != "C":
            continue
        primary = primary_c.get(row["item_id"])
        if not primary:
            continue
        a = normalise_ambiguous(primary.get("ambiguous_with"))
        b = normalise_ambiguous(row.get("ambiguous_with"))
        pairs.append((a, b))
        if a != b:
            disagreements.append({
                "part": "C", "item_id": row["item_id"],
                "target": row.get("target"),
                "field": "ambiguous_with(binary)", "primary": a, "second": b,
            })
    results.append(add_agreement("C", "ambiguous_with(binary)", pairs))

    path = os.path.join(OUT_DIR, "interrater_agreement.csv")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    dis_path = os.path.join(OUT_DIR, "interrater_disagreements.csv")
    with open(dis_path, "w", encoding="utf-8", newline="") as fh:
        fields = ["part", "item_id", "target", "field", "primary", "second"]
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(disagreements)

    print("  %-4s %-28s %5s %8s %8s %7s"
          % ("part", "field", "n", "observed", "expected", "kappa"))
    for row in results:
        print("  %-4s %-28s %5d %8s %8s %7s"
              % (row["part"], row["field"], row["items"],
                 row["observed_agreement"], row["expected_agreement"],
                 row["cohens_kappa"]))
    print("\n%d disagreements written to interrater_disagreements.csv"
          % len(disagreements))

    # Diagnostic: does collapsing "cannot determine" into one category resolve
    # the disagreement? If it does, the problem is the codebook, not the coders.
    diagnostic = []
    for part, fields, source in (("B", PART_B_FIELDS, primary_b),
                                 ("C", PART_C_FIELDS, primary_c)):
        for field in fields:
            pairs = []
            for row in second:
                if row.get("part") != part:
                    continue
                primary = source.get(row["item_id"])
                if not primary:
                    continue
                pairs.append(((primary.get(field) or "").strip(),
                              (row.get(field) or "").strip()))
            diagnostic.append(add_agreement(part, field, pairs, collapse=True))

    diag_path = os.path.join(OUT_DIR, "interrater_diagnostic.csv")
    with open(diag_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(diagnostic[0].keys()))
        writer.writeheader()
        writer.writerows(diagnostic)

    print("\ndiagnostic — kappa after collapsing unclear / n/a into one category:")
    print("  %-4s %-28s %8s %7s" % ("part", "field", "observed", "kappa"))
    for row in diagnostic:
        print("  %-4s %-28s %8s %7s"
              % (row["part"], row["field"], row["observed_agreement"],
                 row["cohens_kappa"]))

    # Harmonised pass: the headline reliability numbers. Only the v1.0 -> v1.1
    # wording change is normalised; every substantive code stays distinct.
    harmonised = []
    for part, fields, source in (("B", PART_B_FIELDS, primary_b),
                                 ("C", PART_C_FIELDS, primary_c)):
        for field in fields:
            pairs = []
            for row in second:
                if row.get("part") != part:
                    continue
                primary = source.get(row["item_id"])
                if not primary:
                    continue
                pairs.append((harmonize_primary(primary.get(field)),
                              (row.get(field) or "").strip()))
            harmonised.append(add_agreement(part, field, pairs))

    harm_path = os.path.join(OUT_DIR, "interrater_agreement_harmonised.csv")
    with open(harm_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(harmonised[0].keys()))
        writer.writeheader()
        writer.writerows(harmonised)

    # Which fields may carry a claim in the paper, and which may not.
    CLAIM_USE = {
        ("B", "write_capability"): "supported",
        ("B", "destructive_capability"): "supported",
        ("B", "auth_mechanism"): "supported with the moderate band stated",
        ("B", "scope_breadth"): "supported with the moderate band stated",
        ("B", "requires_user_secret"): "borderline; report the band",
        ("B", "secret_documented_as_secret"): "not reliable; report as indicative",
        ("B", "readme_warns_about_risk"): "not informative; both coders could not determine it",
        ("C", "desc_states_purpose"): "supported",
        ("C", "desc_states_inputs"): "supported with the moderate band stated",
        ("C", "desc_states_when_to_use"): "not reliable; state the range across both coders",
        ("C", "desc_names_side_effects"): "not reliable; codebook gap, see v1.2 note",
    }
    summary_rows = []
    for row in harmonised:
        row = dict(row)
        row["band"] = kappa_band(row["cohens_kappa"])
        row["claim_use"] = CLAIM_USE.get(
            (row["part"], row["field"]), "review"
        )
        summary_rows.append(row)
    summary_path = os.path.join(OUT_DIR, "interrater_summary.csv")
    with open(summary_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    print("\nharmonised — v1.0/v1.1 wording normalised, headline numbers:")
    print("  %-4s %-28s %8s %8s %7s  %-15s"
          % ("part", "field", "observed", "expected", "kappa", "band"))
    for row in summary_rows:
        print("  %-4s %-28s %8s %8s %7s  %-15s"
              % (row["part"], row["field"], row["observed_agreement"],
                 row["expected_agreement"], row["cohens_kappa"], row["band"]))


if __name__ == "__main__":
    main()
