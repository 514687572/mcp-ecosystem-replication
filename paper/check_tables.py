"""Check that every table and figure caption names a real source table.

Each caption in the manuscript ends with "Source: <file>", naming the result
table the figure or table was built from. This verifies those files exist, and
reports which result tables no caption refers to, so a claim cannot point at a
file that was renamed or removed.

Run: python paper/check_tables.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEX = os.path.join(HERE, "latex", "mcp-ecosystem.tex")
TABLES = os.path.join(ROOT, "results", "tables")


def main():
    with open(TEX, encoding="utf-8") as fh:
        tex = fh.read()

    on_disk = {f for f in os.listdir(TABLES) if f.endswith(".csv")}
    named = set()
    for match in re.finditer(r"Source:\s*\\texttt\{([^}]*)\}", tex):
        raw = match.group(1)
        for part in re.split(r"[,\s]+", raw):
            part = part.strip().rstrip(".")
            if part.endswith(".csv"):
                named.add(part.replace("\\_", "_"))

    missing = sorted(n for n in named if n not in on_disk)
    print("captions name %d source tables" % len(named))
    if missing:
        print("\ncaptions point at files that do not exist:")
        for name in missing:
            print("  MISSING  %s" % name)
    else:
        print("every named source table exists")

    uncited = sorted(on_disk - named)
    print("\nresult tables not named by any caption: %d" % len(uncited))
    for name in uncited[:15]:
        print("  %s" % name)
    if len(uncited) > 15:
        print("  ... and %d more" % (len(uncited) - 15))
    print("\n(these are the tables FACTS.md covers rather than the manuscript;")
    print(" not an error, but a table that should be cited will be noticed here)")

    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
