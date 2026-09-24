"""Check that every number in the abstract and highlights is traceable.

Pre-submission risk: a number that survives one revision of the text but not
the next. This checks three things.

  1. Every figure quoted in the abstract also appears in the body.
  2. Every figure quoted in the highlights also appears in the body.
  3. A hand-maintained list of load-bearing claims still matches the result
     table it came from, so a regenerated table cannot silently invalidate a
     sentence.

Run: python paper/check_numbers.py
"""
import os
import re
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEX = os.path.join(HERE, "latex", "mcp-ecosystem.tex")
HILITE = os.path.join(HERE, "HIGHLIGHTS.txt")
COVER = os.path.join(HERE, "COVER_LETTER.md")
TABLES = os.path.join(ROOT, "results", "tables")
VALID = os.path.join(ROOT, "results", "validation")

# Claims whose sentence would become false if the table changed underneath.
# Each is (label, table, how to find the value, number as written in the text).
CLAIMS = [
    ("published versions", "t01_census_overview.csv",
     ("metric", "published_versions", "value"), 114604),
    ("published servers", "t01_census_overview.csv",
     ("metric", "published_server_names", "value"), 35388),
    ("distinct namespaces", "t01_census_overview.csv",
     ("metric", "distinct_namespaces", "value"), 20540),
    ("servers shipping a package", "t01_census_overview.csv",
     ("metric", "servers_with_packages", "share_of_servers_pct"), 42.9),
    ("servers linking a repository", "t01_census_overview.csv",
     ("metric", "servers_with_repository", "share_of_servers_pct"), 76.7),
    ("tools extracted", "t21_tool_interface_summary.csv",
     ("metric", "extracted tool definitions", "value"), 12065),
    ("descriptions with a description", "t21_tool_interface_summary.csv",
     ("metric", "tools with a description", "share_pct"), 96.4),
    ("descriptions stating when to use", "t21_tool_interface_summary.csv",
     ("metric", "descriptions that state when to use the tool", "share_pct"), 6.2),
]


def strip_tex(text):
    # Drop command names but keep the text inside their braces, otherwise a
    # number wrapped in \textbf{} or \emph{} disappears from the scan.
    text = re.sub(r"\\[a-zA-Z]+\*?", " ", text)
    text = re.sub(r"[{}\\$]", " ", text)
    return text


def numbers_in(text):
    text = strip_tex(text)
    found = set()
    for match in re.finditer(r"(\d[\d,]*\.?\d*)", text):
        raw = match.group(1).replace(",", "")
        found.add(raw)
        if raw.endswith(".0"):
            found.add(raw[:-2])
    return found


def section(text, start, end):
    m = re.search(re.escape(start) + r"(.*?)" + re.escape(end), text, re.DOTALL)
    return m.group(1) if m else ""


def main():
    with open(TEX, encoding="utf-8") as fh:
        tex = fh.read()
    with open(HILITE, encoding="utf-8") as fh:
        highlights = "\n".join(line for line in fh
                               if not line.strip().lower().startswith("highlights"))

    abstract = section(tex, r"\begin{abstract}", r"\end{abstract}")
    body = tex.split(r"\begin{abstract}", 1)[-1]
    body = body.replace(abstract, " ", 1)

    body_numbers = numbers_in(body)
    problems = []

    cover = ""
    if os.path.isfile(COVER):
        with open(COVER, encoding="utf-8") as fh:
            cover = fh.read()
        # The ORCID and the DOI are identifiers, not quantities. Scanning their
        # digit groups produces meaningless mismatches.
        cover = re.sub(r"ORCID\s*[\d-]+", " ", cover, flags=re.IGNORECASE)
        cover = re.sub(r"10\.\d{4,5}/[^\s<>)]+", " ", cover)

    # Quantities that describe the replication package rather than the paper.
    # The body has no reason to state them, so they are checked against the
    # package itself instead.
    package_facts = {}
    tables_dir = os.path.join(ROOT, "results", "tables")
    if os.path.isdir(tables_dir):
        package_facts[str(len([f for f in os.listdir(tables_dir)
                               if f.endswith(".csv")]))] = "result tables on disk"

    for label, source in (("abstract", abstract), ("highlights", highlights),
                          ("cover letter", cover)):
        if not source:
            continue
        for value in sorted(numbers_in(source), key=lambda v: -len(v)):
            if value in body_numbers:
                continue
            # Allow a different rounding of the same quantity.
            alt = {value, value.rstrip("0").rstrip(".")}
            if any(a in body_numbers for a in alt if a):
                continue
            if value in package_facts:
                continue
            problems.append("%s quotes %s but the body does not" % (label, value))

    # Load-bearing claims against their source tables.
    claim_problems = []
    for label, table, (key_col, key_val, value_col), expected in CLAIMS:
        path = os.path.join(TABLES, table)
        if not os.path.isfile(path):
            claim_problems.append("%s: table %s missing" % (label, table))
            continue
        frame = pd.read_csv(path)
        row = frame[frame[key_col].astype(str) == key_val]
        if row.empty:
            claim_problems.append("%s: row %r not in %s" % (label, key_val, table))
            continue
        actual = float(row.iloc[0][value_col])
        if abs(actual - expected) > 0.05:
            claim_problems.append("%s: text implies %s, table says %s"
                                  % (label, expected, actual))

    if problems:
        print("ABSTRACT / HIGHLIGHT TRACEABILITY")
        for p in problems:
            print("  FAIL  %s" % p)
    else:
        print("abstract and highlights: every quoted number appears in the body")

    if claim_problems:
        print("\nLOAD-BEARING CLAIMS")
        for p in claim_problems:
            print("  FAIL  %s" % p)
    else:
        print("load-bearing claims: all %d match their source tables" % len(CLAIMS))

    return 1 if (problems or claim_problems) else 0


if __name__ == "__main__":
    sys.exit(main())
