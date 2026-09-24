"""Check that every \\cite in the manuscript has a bib entry, and report unused entries."""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "latex", "mcp-ecosystem.tex")
BIB = os.path.join(HERE, "latex", "mcp-refs.bib")


def main():
    with open(TEX, encoding="utf-8") as fh:
        tex = fh.read()
    with open(BIB, encoding="utf-8") as fh:
        bib = fh.read()

    cited = set()
    for match in re.finditer(r"\\cite[a-zA-Z]*\{([^}]*)\}", tex):
        for key in match.group(1).split(","):
            key = key.strip()
            if key:
                cited.add(key)

    defined = set(re.findall(r"@\w+\s*\{\s*([^,\s]+)\s*,", bib))

    print("cited   : %d" % len(cited))
    print("defined : %d" % len(defined))
    missing = sorted(cited - defined)
    unused = sorted(defined - cited)
    print("\nMISSING (cited but not defined): %s" % (missing or "none"))
    print("\nUNUSED (defined but not cited): %s" % (unused or "none"))

    # Report label/reference balance too, since JSS requires numbered cross-refs.
    labels = set(re.findall(r"\\label\{([^}]*)\}", tex))
    refs = set(re.findall(r"\\ref\{([^}]*)\}", tex))
    print("\nlabels  : %d" % len(labels))
    print("broken refs: %s" % (sorted(refs - labels) or "none"))
    print("unreferenced labels: %s" % (sorted(labels - refs) or "none"))

    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
