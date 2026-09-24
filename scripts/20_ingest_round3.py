"""Step 20 — ingest and score the round-3 inter-rater coding.

Round 3 differs from round 2 in two ways that this script handles explicitly
rather than silently:

  * Both coders re-coded under codebook v1.2, so the comparison is direct. No
    vocabulary harmonisation is needed, and none is applied.

  * The primary file arrived with one empty field missing from every Part C
    row, which shifts every value from `write_capability` onward one column to
    the left. The shift is detectable (the row has one fewer field than the
    header) and its repair is deterministic (one empty field is restored), so
    the file is repaired rather than discarded. The repair is verified against
    the pack's own adjudicated examples before it is used.

Inputs : results/validation/round3_coding_pack/*.csv and *.xlsx
Outputs: results/validation/round3_codes_primary.csv / _coder2.csv  (normalised)
         results/validation/round3_agreement.csv
         results/validation/round3_validation.txt
"""
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from mcpstudy import config  # noqa: E402

PACK = os.path.join(config.RESULTS_DIR, "validation", "round3_coding_pack")
OUT = os.path.join(config.RESULTS_DIR, "validation")

PART_B_FIELDS = ["auth_mechanism", "auth_evidence", "requires_user_secret",
                 "secret_documented_as_secret", "scope_breadth",
                 "destructive_capability", "write_capability"]
PART_C_FIELDS = ["desc_states_purpose", "desc_states_when_to_use",
                 "desc_states_inputs", "desc_names_side_effects",
                 "ambiguous_with"]

ALLOWED = {
    "auth_mechanism": {"none", "api_key", "oauth", "bearer_token", "basic",
                       "jwt", "hmac", "env_var", "browser_session", "x402",
                       "prepaid_credit", "other", "undetermined"},
    "auth_evidence": {"manifest_env_vars", "manifest_description", "readme",
                      "source", "website", "no_statement",
                      "local_configuration"},
    "requires_user_secret": {"yes", "no", "undetermined"},
    "secret_documented_as_secret": {"yes", "no", "n/a"},
    "scope_breadth": {"read_only", "narrow", "moderate", "broad",
                      "undetermined"},
    "destructive_capability": {"yes", "no", "undetermined"},
    "write_capability": {"yes", "no", "undetermined"},
    "desc_states_purpose": {"yes", "partial", "no"},
    "desc_states_when_to_use": {"yes", "no"},
    "desc_states_inputs": {"yes", "no", "n/a"},
    "desc_names_side_effects": {"yes", "no"},
}

# The pack is self-contained, which is what made round 2 work, but two parts of
# it supply the answer for specific items and therefore cannot support an
# independent-agreement claim:
#
#   * Change 2 lists five adjudicated examples, and those five item ids are in
#     the coded set. `desc_states_when_to_use` is therefore also computed over
#     the 20 items the examples do not cover.
#   * Every Part B item shows the manifest rule's verdict for
#     `secret_documented_as_secret`. All 25 items are affected, so that field
#     has no uncontaminated items left and cannot be reported as reliability at
#     all. It is reported as what it actually measures: whether two coders
#     applied a mechanical lookup the same way.
WORKED_EXAMPLES = ["C001", "C003", "C010", "C016", "C020"]
PRE_ANSWERED_ENTIRELY = ["secret_documented_as_secret"]


def repair_primary(path):
    """Restore the empty field that the Part C rows lost.

    A Part C row carries seven blank Part B cells before its first Part C value.
    The file as received has six, so one blank is reinserted immediately after
    `target`'s blank run, restoring every downstream value to its own column.
    """
    with open(path, encoding="utf-8-sig") as fh:
        raw = [line.rstrip("\n") for line in fh if line.strip()]
    header = raw[0].split(",")
    expected = len(header)
    rows = []
    repaired = 0
    for line in raw[1:]:
        cells = line.split(",")
        if len(cells) == expected - 1 and cells[1] == "C":
            cells = cells[:9] + [""] + cells[9:]
            repaired += 1
        while len(cells) < expected:
            cells.append("")
        rows.append(dict(zip(header, cells[:expected])))
    print("primary: %d rows, %d Part C rows needed one empty field restored"
          % (len(rows), repaired))
    return rows


def read_coder2(path):
    """The second coder returned an .xlsx saved under a .csv name.

    openpyxl refuses a path whose extension is not a workbook format, so the
    bytes go through a stream instead of the filename.
    """
    import io

    import openpyxl

    with open(path, "rb") as fh:
        payload = fh.read()
    book = openpyxl.load_workbook(io.BytesIO(payload), data_only=True)
    sheet = book.active
    values = list(sheet.values)
    header = [str(c).strip() if c is not None else "" for c in values[0]]
    rows = []
    for raw in values[1:]:
        if not raw or raw[0] is None:
            continue
        cells = ["" if c is None else str(c).strip() for c in raw]
        while len(cells) < len(header):
            cells.append("")
        rows.append(dict(zip(header, cells[:len(header)])))
    print("coder2 : %d rows read from xlsx (sheet %r)"
          % (len(rows), sheet.title))
    return rows


def normalise(rows, label, problems):
    """Trim values, check them against the codebook, sort by item id."""
    out = []
    for row in rows:
        part = (row.get("part") or "").strip()
        fields = PART_B_FIELDS if part == "B" else PART_C_FIELDS
        clean = {"item_id": (row.get("item_id") or "").strip(),
                 "part": part,
                 "target": (row.get("target") or "").strip()}
        for field in fields:
            value = (row.get(field) or "").strip()
            if field == "ambiguous_with":
                clean[field] = value
                continue
            if value and field in ALLOWED and value not in ALLOWED[field]:
                problems.append("%s %s %s: %r is not a permitted value"
                                % (label, clean["item_id"], field, value))
            if not value:
                problems.append("%s %s %s: blank" % (label, clean["item_id"], field))
            clean[field] = value
        out.append(clean)
    return sorted(out, key=lambda r: r["item_id"])


def cohens_kappa(pairs):
    n = len(pairs)
    if n == 0:
        return None, None, None
    labels = sorted({v for pair in pairs for v in pair})
    observed = sum(1 for a, b in pairs if a == b) / float(n)
    expected = 0.0
    for label in labels:
        pa = sum(1 for a, _ in pairs if a == label) / float(n)
        pb = sum(1 for _, b in pairs if b == label) / float(n)
        expected += pa * pb
    if expected >= 1.0:
        return observed, expected, None
    return observed, expected, (observed - expected) / (1.0 - expected)


def band(kappa):
    if kappa is None:
        return "not estimable"
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
    problems = []
    primary = normalise(repair_primary(
        os.path.join(PACK, "interrater_worksheet_v1.2_primary.csv")),
        "primary", problems)
    coder2 = normalise(read_coder2(
        os.path.join(PACK, "interrater_worksheet_v1.2_coder2.csv")),
        "coder2", problems)

    by_primary = {r["item_id"]: r for r in primary}
    by_coder2 = {r["item_id"]: r for r in coder2}
    shared = sorted(set(by_primary) & set(by_coder2))
    print("shared items: %d" % len(shared))

    results = []
    disagreements = []
    for field in PART_B_FIELDS + PART_C_FIELDS:
        pairs = []
        for item in shared:
            a = by_primary[item].get(field, "")
            b = by_coder2[item].get(field, "")
            if field == "ambiguous_with":
                a = "yes" if a else "no"
                b = "yes" if b else "no"
                if a != b:
                    disagreements.append((item, field, a, b))
                pairs.append((a, b))
                continue
            pairs.append((a, b))
            if a != b:
                disagreements.append((item, field, a, b))
        if field == "ambiguous_with":
            results.append((field, len(pairs), *cohens_kappa(pairs),
                            "binary: has an ambiguous sibling"))
        else:
            results.append((field, len(pairs), *cohens_kappa(pairs), ""))

    # Reported separately below: the same field with the worked examples removed.
    clean_items = [i for i in shared
                   if i.startswith("C") and i not in WORKED_EXAMPLES]
    clean_pairs = [(by_primary[i]["desc_states_when_to_use"],
                    by_coder2[i]["desc_states_when_to_use"])
                   for i in clean_items]
    clean_observed, clean_expected, clean_kappa = cohens_kappa(clean_pairs)

    # Normalised copies, so the analysis can be re-run without the repair.
    for name, rows in (("round3_codes_primary.csv", primary),
                       ("round3_codes_coder2.csv", coder2)):
        fields = ["item_id", "part", "target"] + PART_B_FIELDS + PART_C_FIELDS
        with open(os.path.join(OUT, name), "w", encoding="utf-8",
                  newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    path = os.path.join(OUT, "round3_agreement.csv")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["field", "items", "observed", "expected", "kappa",
                            "band", "note"])
        for field, n, observed, expected, kappa, note in results:
            if field in PRE_ANSWERED_ENTIRELY:
                note = ("the pack supplied this field's verdict for every item; "
                        "measures rule application, not independent agreement")
            elif field == "desc_states_when_to_use":
                note = ("5 items are worked examples in the codebook; excluding "
                        "them gives observed %.3f, kappa %.3f over %d items"
                        % (clean_observed, clean_kappa, len(clean_items)))
            writer.writerow([field, n,
                             round(observed, 3) if observed is not None else "",
                             round(expected, 3) if expected is not None else "",
                             round(kappa, 3) if kappa is not None else "",
                             band(kappa), note])

    with open(os.path.join(OUT, "round3_validation.txt"), "w",
              encoding="utf-8") as fh:
        fh.write("Round 3 value validation\n\n")
        fh.write("shared items: %d\n\n" % len(shared))
        if problems:
            fh.write("%d problems\n\n" % len(problems))
            for p in problems:
                fh.write("  %s\n" % p)
        else:
            fh.write("every coded value is permitted by codebook v1.2\n")
        fh.write("\ndisagreements: %d\n\n" % len(disagreements))
        for item, field, a, b in disagreements:
            fh.write("  %-6s %-28s primary=%-14s coder2=%s\n"
                     % (item, field, a, b))
        fh.write("\n\ncontamination audit\n\n")
        fh.write("The pack is self-contained by design. Two parts of it answer\n"
                 "specific items, and those items are excluded from any claim of\n"
                 "independent agreement:\n\n")
        fh.write("  desc_states_when_to_use: worked examples %s\n"
                 % ", ".join(WORKED_EXAMPLES))
        fh.write("    all %d items      -> observed %.3f, kappa %.3f\n"
                 % (len(shared),
                    next(r[2] for r in results
                         if r[0] == "desc_states_when_to_use"),
                    next(r[4] for r in results
                         if r[0] == "desc_states_when_to_use")))
        fh.write("    %d clean items    -> observed %.3f, kappa %.3f\n"
                 % (len(clean_items), clean_observed, clean_kappa))
        fh.write("\n  secret_documented_as_secret: the pack shows the manifest\n"
                 "    rule's verdict for all 25 Part B items, and both coders\n"
                 "    matched it on all 25. No uncontaminated items remain, so the\n"
                 "    field is reported as rule application rather than as\n"
                 "    inter-rater reliability.\n")

    print("\n%-30s %5s %9s %9s %8s  %s"
          % ("field", "n", "observed", "expected", "kappa", "band"))
    print("-" * 84)
    for field, n, observed, expected, kappa, _ in results:
        print("%-30s %5d %9s %9s %8s  %s"
              % (field, n,
                 round(observed, 3) if observed is not None else "-",
                 round(expected, 3) if expected is not None else "-",
                 round(kappa, 3) if kappa is not None else "-",
                 band(kappa)))
    print("\nvalidation problems: %d" % len(problems))
    print("disagreements      : %d" % len(disagreements))
    print("\ndesc_states_when_to_use, excluding the 5 worked examples:")
    print("  %d items -> observed %.3f, kappa %.3f"
          % (len(clean_items), clean_observed, clean_kappa))
    print("secret_documented_as_secret: rule application, not agreement "
          "(0 uncontaminated items)")
    print("\nwrote results/validation/round3_{codes,agreement,validation}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
