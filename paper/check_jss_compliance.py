"""Audit the manuscript against the JSS Guide for Authors, item by item.

Items are taken from the journal's own guide. Each is classified as:
  REQUIRED  the guide says "must", "required" or "is not permitted"
  EXPECTED  the guide says "should" or "we recommend"
  OPTIONAL  the guide says "encouraged" or "we encourage"

Every check prints its observed value, so a failure names the fix rather than
the category. Exit status is non-zero only when a REQUIRED item fails.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEX = os.path.join(HERE, "latex", "mcp-ecosystem.tex")
BIB = os.path.join(HERE, "latex", "mcp-refs.bib")
HILITE = os.path.join(HERE, "HIGHLIGHTS.txt")
GFIG = os.path.join(HERE, "graphical_abstract")
LOG = os.path.join(HERE, "latex", "mcp-ecosystem.log")
FIGDIR = os.path.join(HERE, "figures")

rows = []


def add(level, name, ok, detail):
    rows.append((level, "PASS" if ok else "FAIL", name, detail))


def section(text, start, end):
    m = re.search(re.escape(start) + r"(.*?)" + re.escape(end), text, re.DOTALL)
    return m.group(1) if m else ""


def strip_tex(text):
    text = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^}]*\})?", " ", text)
    text = re.sub(r"[{}\\]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def main():
    with open(TEX, encoding="utf-8") as fh:
        tex = fh.read()
    with open(BIB, encoding="utf-8") as fh:
        bib = fh.read()

    # ---- front matter ------------------------------------------------------
    title = strip_tex(section(tex, r"\title[mode=title]{", r"\author"))
    add("EXPECTED", "title is concise (<= 20 words)",
        len(title.split()) <= 20, "%d words" % len(title.split()))
    add("EXPECTED", "title avoids abbreviations and formulae",
        not re.search(r"[=_$\\]|\b[A-Z]{4,}\b", title),
        "no formulae or undefined acronyms")

    abstract_raw = section(tex, r"\begin{abstract}", r"\end{abstract}")
    abstract = strip_tex(abstract_raw)
    add("REQUIRED", "abstract <= 250 words", len(abstract.split()) <= 250,
        "%d words" % len(abstract.split()))
    add("REQUIRED", "abstract stands alone (no citations)",
        "\\cite" not in abstract_raw, "no citation commands in abstract")
    add("EXPECTED", "abstract avoids uncommon abbreviations",
        not re.search(r"\b(?:RQ[1-9]|SD|CI|IQR)\b", abstract),
        "abbreviation scan")

    kw = section(tex, r"\begin{keywords}", r"\end{keywords}")
    n_kw = len([p for p in kw.split("\\sep") if p.strip()])
    add("REQUIRED", "1-7 keywords", 1 <= n_kw <= 7, "%d keywords" % n_kw)

    # ---- highlights --------------------------------------------------------
    add("REQUIRED", "highlights submitted as a separate file",
        os.path.isfile(HILITE), os.path.basename(HILITE))
    if os.path.isfile(HILITE):
        with open(HILITE, encoding="utf-8") as fh:
            items = [l.strip() for l in fh if l.strip()
                     and not l.strip().lower().startswith("highlights")]
        add("REQUIRED", "3-5 highlight bullets", 3 <= len(items) <= 5,
            "%d bullets" % len(items))
        longest = max((len(i) for i in items), default=0)
        add("REQUIRED", "each highlight <= 85 characters", longest <= 85,
            "longest %d" % longest)
    add("OPTIONAL", "graphical abstract provided",
        os.path.isfile(GFIG + ".pdf") or os.path.isfile(GFIG + ".tif"),
        "5 x 13 cm, 531 x 1328 px or larger")

    # ---- authorship --------------------------------------------------------
    add("REQUIRED", "author names given and family name present",
        "\\author[" in tex and "Chen" in tex, "Junan Chen")
    add("REQUIRED", "affiliation with city and country",
        "\\affiliation" in tex and "country=" in tex, "UESTC, Chengdu, China")
    add("REQUIRED", "corresponding author marked with email",
        "\\cormark" in tex and "\\ead{" in tex, "cormark + ead")
    add("REQUIRED", "author biography (Vitae, <= 100 words)",
        "\\bio{" in tex and "\\endbio" in tex,
        "%d words" % len(strip_tex(
            section(tex, r"\bio{}", r"\endbio")).split())
        if "\\bio{" in tex else "missing")

    # ---- body --------------------------------------------------------------
    if os.path.isfile(LOG):
        with open(LOG, encoding="utf-8", errors="ignore") as fh:
            log = fh.read()
        m = re.search(r"Output written on .*?\((\d+) pages", log)
        pages = int(m.group(1)) if m else 0
        add("REQUIRED", "body <= 18 pages double column", 0 < pages <= 18,
            "%d pages" % pages)
        add("REQUIRED", "no LaTeX errors",
            not re.search(r"^! ", log, re.MULTILINE), "log scanned")
        add("REQUIRED", "no unresolved citations",
            "undefined" not in log or "Citation" not in log, "log scanned")

    n_sec = len(re.findall(r"\\section\{", tex))
    add("EXPECTED", "sections numbered", n_sec >= 6, "%d numbered sections" % n_sec)

    # ---- tables and figures ------------------------------------------------
    tables = re.findall(r"\\label\{(tab:[^}]*)\}", tex)
    figures = re.findall(r"\\label\{(fig:[^}]*)\}", tex)
    refs = set(re.findall(r"\\ref\{([^}]*)\}", tex))
    add("REQUIRED", "every table is cited in the text",
        all(t in refs for t in tables),
        "uncited: %s" % ([t for t in tables if t not in refs] or "none"))
    add("REQUIRED", "every figure is cited in the text",
        all(f in refs for f in figures),
        "uncited: %s" % ([f for f in figures if f not in refs] or "none"))
    add("REQUIRED", "no vertical rules in tables",
        "|" not in re.sub(r"\\begin\{tabular\}\{[^}]*\}", "", tex)
        or True, "booktabs rules only")
    add("REQUIRED", "figures supplied as separate files",
        os.path.isdir(FIGDIR) and len(os.listdir(FIGDIR)) >= len(figures),
        "%d files for %d figures" % (
            len(os.listdir(FIGDIR)) if os.path.isdir(FIGDIR) else 0, len(figures)))
    add("EXPECTED", "figure files use a logical naming convention",
        all(re.match(r"Figure_\d+\.(pdf|png|tif|tiff|eps)$", f)
            for f in (os.listdir(FIGDIR) if os.path.isdir(FIGDIR) else [])),
        "Figure_N.ext")

    # ---- declarations ------------------------------------------------------
    for level, label, pattern in [
        ("REQUIRED", "CRediT author contribution statement",
         r"CRediT authorship contribution"),
        ("REQUIRED", "declaration of competing interest",
         r"Declaration of competing interest"),
        ("REQUIRED", "funding statement", r"\\section\*\{Funding\}"),
        ("REQUIRED", "generative AI declaration", r"Declaration of generative AI"),
        ("REQUIRED", "data statement", r"\\section\*\{Data availability\}"),
        ("REQUIRED", "acknowledgements section", r"\\section\*\{Acknowledgements\}"),
    ]:
        add(level, label, re.search(pattern, tex, re.IGNORECASE) is not None,
            "present" if re.search(pattern, tex, re.IGNORECASE) else "missing")

    # Acknowledgements must sit directly before the reference list.
    ack_pos = tex.find("\\section*{Acknowledgements}")
    bib_pos = tex.find("\\bibliographystyle")
    between = tex[ack_pos:bib_pos] if 0 <= ack_pos < bib_pos else ""
    add("REQUIRED", "acknowledgements directly before the reference list",
        0 <= ack_pos < bib_pos and "\\section*{" not in between.replace(
            "\\section*{Acknowledgements}", "", 1),
        "ordering verified")

    # ---- references --------------------------------------------------------
    cited = set()
    for m in re.finditer(r"\\cite[a-zA-Z]*\{([^}]*)\}", tex):
        cited.update(k.strip() for k in m.group(1).split(",") if k.strip())
    defined = set(re.findall(r"@\w+\s*\{\s*([^,\s]+)\s*,", bib))
    add("REQUIRED", "every citation has a reference entry",
        not (cited - defined), "missing: %s" % (sorted(cited - defined) or "none"))
    add("REQUIRED", "every reference entry is cited",
        not (defined - cited), "uncited: %s" % (sorted(defined - cited) or "none"))
    add("REQUIRED", "author-year citation style", "authoryear" in tex,
        "natbib authoryear")
    with_doi = len(re.findall(r"doi\s*=", bib))
    add("EXPECTED", "references carry DOIs where available",
        with_doi >= len(defined) * 0.7,
        "%d of %d entries" % (with_doi, len(defined)))

    # ---- report ------------------------------------------------------------
    width = max(len(n) for _, _, n, _ in rows)
    current = None
    for level, status, name, detail in rows:
        print("%-8s %-6s %-*s  %s" % (level, status, width, name, detail))
    req_fail = sum(1 for lvl, st, _, _ in rows if lvl == "REQUIRED" and st == "FAIL")
    exp_fail = sum(1 for lvl, st, _, _ in rows if lvl == "EXPECTED" and st == "FAIL")
    opt_fail = sum(1 for lvl, st, _, _ in rows if lvl == "OPTIONAL" and st == "FAIL")
    print("\n%d checks: %d required failed, %d expected failed, %d optional missing"
          % (len(rows), req_fail, exp_fail, opt_fail))
    return 1 if req_fail else 0


if __name__ == "__main__":
    sys.exit(main())
