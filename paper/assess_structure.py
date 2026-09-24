"""Report the shape of the manuscript: words per section, evidence density.

Used to judge balance before submission. A section that is short relative to
its role, or a claim without a nearby table reference, is a review risk.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "latex", "mcp-ecosystem.tex")


def strip_tex(text):
    text = re.sub(r"\\begin\{(table\*?|figure\*?|tabular\*?)\}.*?\\end\{\1\}",
                  " ", text, flags=re.S)
    text = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^}]*\})?", " ", text)
    text = re.sub(r"[{}\\]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def main():
    with open(TEX, encoding="utf-8") as fh:
        tex = fh.read()
    tex = "\n".join(l for l in tex.splitlines()
                    if not l.lstrip().startswith("%"))
    body = tex.split("\\begin{document}", 1)[-1]
    body = body.split("\\bibliographystyle", 1)[0]

    # Split on top-level sections.
    parts = re.split(r"\\section\*?\{([^}]*)\}", body)
    total = len(strip_tex(body).split())
    rows = []
    for i in range(1, len(parts), 2):
        title = parts[i]
        content = parts[i + 1] if i + 1 < len(parts) else ""
        words = len(strip_tex(content).split())
        refs = len(re.findall(r"\\ref\{|\\citep?\{", content))
        rows.append((title, words, refs))

    print("%-52s %7s %7s %8s" % ("section", "words", "refs", "share"))
    print("-" * 78)
    for title, words, refs in rows:
        print("%-52s %7d %7d %7.1f%%"
              % (title[:52], words, refs, 100.0 * words / total))
    print("-" * 78)
    print("%-52s %7d" % ("TOTAL (excluding tables/figures)", total))

    # Claims and their grounding.
    print("\nevidence density")
    print("  tables           : %d" % len(re.findall(r"\\begin\{table\*?\}", tex)))
    print("  figures          : %d" % len(re.findall(r"\\begin\{figure\*?\}", tex)))
    print("  table/figure refs: %d" % len(re.findall(r"\\ref\{(?:tab|fig):", tex)))
    print("  citations        : %d" % len(re.findall(r"\\citep?\{", tex)))
    print("  citations per 1k words: %.1f" % (1000.0 *
          len(re.findall(r"\\citep?\{", tex)) / total))
    print("  refs per 1k words     : %.1f" % (1000.0 *
          len(re.findall(r"\\ref\{", tex)) / total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
