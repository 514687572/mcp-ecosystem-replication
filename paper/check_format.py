"""Check the manuscript against the JSS Guide for Authors hard requirements.

Each check is independent and prints PASS / FAIL / WARN with the observed value,
so a failure points at a specific fix rather than at "format".
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "latex", "mcp-ecosystem.tex")
HIGHLIGHTS = os.path.join(HERE, "HIGHLIGHTS.txt")
LOG = os.path.join(HERE, "latex", "mcp-ecosystem.log")

results = []


def check(name, ok, detail, level="FAIL"):
    results.append((level if not ok else "PASS", name, detail))


def section(text, start, end):
    m = re.search(re.escape(start) + r"(.*?)" + re.escape(end), text, re.DOTALL)
    return m.group(1) if m else ""


def strip_latex(text):
    text = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^}]*\})?", " ", text)
    text = re.sub(r"[{}\\]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def main():
    with open(TEX, encoding="utf-8") as fh:
        tex = fh.read()

    # Abstract: <= 250 words, no citations.
    abstract = strip_latex(section(tex, r"\begin{abstract}", r"\end{abstract}"))
    words = len(abstract.split())
    check("abstract <= 250 words", words <= 250, "%d words" % words)
    check("abstract contains no citations", "\\cite" not in
          section(tex, r"\begin{abstract}", r"\end{abstract}"), "no \\cite in abstract")

    # Highlights: 3-5 items, each <= 85 characters, separate file.
    check("highlights are a separate file", os.path.isfile(HIGHLIGHTS), HIGHLIGHTS)
    check("highlights not embedded in the manuscript",
          "\\begin{highlights}" not in tex, "no highlights environment")
    if os.path.isfile(HIGHLIGHTS):
        with open(HIGHLIGHTS, encoding="utf-8") as fh:
            lines = [l.strip() for l in fh if l.strip()]
        items = [l for l in lines if not l.lower().startswith("highlights")]
        check("3-5 highlight items", 3 <= len(items) <= 5,
              "%d items" % len(items))
        longest = max((len(i) for i in items), default=0)
        check("each highlight <= 85 characters", longest <= 85,
              "longest %d characters" % longest)

    # Keywords: 1-7.
    kw = section(tex, r"\begin{keywords}", r"\end{keywords}")
    n_kw = len([p for p in kw.split("\\sep") if p.strip()])
    check("1-7 keywords", 1 <= n_kw <= 7, "%d keywords" % n_kw)

    # Length: JSS allows 18 pages double column.
    if os.path.isfile(LOG):
        with open(LOG, encoding="utf-8", errors="ignore") as fh:
            log = fh.read()
        m = re.search(r"Output written on .*?\((\d+) pages", log)
        pages = int(m.group(1)) if m else 0
        check("body <= 18 pages (double column)", 0 < pages <= 18,
              "%d pages" % pages)
        check("no unresolved citations", "Citation" not in log or
              "undefined" not in log, "log scanned")
        check("no LaTeX errors", not re.search(r"^! ", log, re.MULTILINE),
              "log scanned")

    # Required declarations.
    for label, pattern in [
        ("CRediT statement", r"CRediT authorship contribution"),
        ("declaration of competing interest", r"Declaration of competing interest"),
        ("data availability statement", r"Data availability"),
        ("generative AI declaration", r"Declaration of generative AI"),
    ]:
        check(label, re.search(pattern, tex, re.IGNORECASE) is not None,
              "present" if re.search(pattern, tex, re.IGNORECASE) else "missing")

    # Author-year citation style, alphabetical bibliography.
    check("author-year citation style", "authoryear" in tex, "natbib authoryear")

    width = max(len(n) for _, n, _ in results)
    for level, name, detail in results:
        print("%-5s %-*s  %s" % (level, width, name, detail))
    failed = sum(1 for lvl, _, _ in results if lvl == "FAIL")
    print("\n%d checks, %d failed" % (len(results), failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
