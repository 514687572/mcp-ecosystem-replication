#!/usr/bin/env python3
"""Measure the surface features that AI-text detectors key on.

No detector score can be computed offline and detectors disagree with each
other, so this script measures the features that correlate with machine-written
academic prose and reports them before and after a revision:

  * em-dash density, the strongest and most easily measured marker
  * sentence-length spread (machine prose is uniform)
  * formulaic connectives and meta-commentary
  * repeated sentence openings, especially sentence-initial "The"
  * parallel triads and "not X but Y" constructions
  * passive-voice density

The target is the range normal for single-author engineering papers, not a
particular vendor's threshold.

Usage:
    python ai_style_check.py
    python ai_style_check.py --json
    python ai_style_check.py --tex latex/mcp-ecosystem.tex
"""
import argparse
import io
import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TEX = os.path.join(HERE, "latex", "mcp-ecosystem.tex")

FORMULAIC = [
    r"\bmoreover\b", r"\bfurthermore\b", r"\bin addition\b", r"\bit is worth\b",
    r"\bit is important\b", r"\bit is notable\b", r"\bnotably\b", r"\bcrucially\b",
    r"\bimportantly\b", r"\binterestingly\b", r"\boverall\b", r"\bin summary\b",
    r"\bthis is (?:a|the) \w+", r"\blet us\b", r"\bdeliberately\b",
    r"\bexplicitly\b", r"\bthe key (?:insight|point|finding)\b",
    r"\bplays? a (?:key|critical|vital) role\b", r"\bdelve\b",
    r"\btapestry\b", r"\bunderscores?\b", r"\bhighlights? the\b",
    r"\bsheds? light\b", r"\bit is clear that\b", r"\bneedless to say\b",
    r"\bin today's\b", r"\bwhen it comes to\b",
]


def body_text(tex):
    body = tex.split("\\begin{document}", 1)[-1]
    body = body.split("\\bibliographystyle", 1)[0]
    body = re.sub(
        r"\\begin\{(table\*?|figure\*?|tabular\*?|lstlisting|equation|keywords)\}"
        r".*?\\end\{\1\}", " ", body, flags=re.S)
    body = re.sub(r"\\item\s", "\n", body)
    body = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^}]*\})?", " ", body)
    body = body.replace("{", " ").replace("}", " ").replace("~", " ")
    body = re.sub(r"---", " EMDASH ", body)
    body = re.sub(r"--", " EMDASH ", body)
    return body


def sentences(text):
    text = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z(])", text)
    return [p.strip() for p in parts if len(p.strip().split()) >= 4]


def analyse(tex):
    tex_nocomment = "\n".join(
        line for line in tex.splitlines() if not line.lstrip().startswith("%")
    )
    text = body_text(tex_nocomment)
    words = re.findall(r"[A-Za-z][A-Za-z'\-]+", text)
    sents = sentences(text)
    lens = [len(s.split()) for s in sents]
    emdash = len(re.findall(r"\bEMDASH\b", text))
    openings = [re.match(r"([A-Za-z']+)", s).group(1).lower()
                for s in sents if re.match(r"([A-Za-z']+)", s)]
    top_open = sorted(set((o, openings.count(o)) for o in openings),
                      key=lambda t: -t[1])[:5]
    the_initial = sum(1 for o in openings if o == "the")
    formulaic = {p.strip("\\b"): len(re.findall(p, tex_nocomment, re.I))
                 for p in FORMULAIC}
    triads = len(re.findall(r"\b\w+,\s+\w+,\s+and\s+\w+\b", text))
    notxbuty = len(re.findall(
        r"\b(?:is|are|was|were)\s+not\s+\w+[^.]{0,40}\bbut\b", text, re.I))
    passive = len(re.findall(
        r"\b(?:is|are|was|were|be|been|being)\s+\w+(?:ed|en)\b", text, re.I))

    def per1000(n):
        return round(1000.0 * n / len(words), 1) if words else 0.0

    return {
        "words": len(words),
        "sentences": len(sents),
        "mean_sentence_words": round(statistics.mean(lens), 1) if lens else 0,
        "sd_sentence_words": round(statistics.pstdev(lens), 1) if lens else 0,
        "min_sentence_words": min(lens) if lens else 0,
        "max_sentence_words": max(lens) if lens else 0,
        "em_dashes": emdash,
        "em_dashes_per_1000_words": per1000(emdash),
        "formulaic_total": sum(formulaic.values()),
        "formulaic_per_1000_words": per1000(sum(formulaic.values())),
        "triads_per_1000_words": per1000(triads),
        "not_x_but_y": notxbuty,
        "passive_per_1000_words": per1000(passive),
        "the_initial_sentences": the_initial,
        "the_initial_pct": round(100.0 * the_initial / len(sents), 1) if sents else 0,
        "top_sentence_openings": top_open,
        "formulaic_detail": {k: v for k, v in formulaic.items() if v},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tex", default=DEFAULT_TEX)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--baseline", default=None,
                    help="path to a saved JSON result to diff against")
    args = ap.parse_args()

    with io.open(args.tex, encoding="utf-8") as fh:
        tex = fh.read()
    result = analyse(tex)

    if args.baseline and os.path.isfile(args.baseline):
        # Accept a BOM or UTF-16: these files are often produced by shell
        # redirection on Windows, which defaults to UTF-16.
        with io.open(args.baseline, encoding="utf-8-sig") as fh:
            raw = fh.read()
        try:
            base = json.loads(raw)
        except ValueError:
            with io.open(args.baseline, encoding="utf-16") as fh2:
                base = json.load(fh2)
        print("%-32s %10s %10s %10s" % ("metric", "before", "after", "change"))
        for key in ("em_dashes_per_1000_words", "mean_sentence_words",
                    "sd_sentence_words", "formulaic_total",
                    "formulaic_per_1000_words", "triads_per_1000_words",
                    "not_x_but_y", "passive_per_1000_words",
                    "the_initial_pct", "words"):
            before = base.get(key)
            after = result.get(key)
            if isinstance(before, (int, float)) and isinstance(after, (int, float)):
                delta = round(after - before, 1)
                flag = ""
                if key in ("em_dashes_per_1000_words", "formulaic_per_1000_words",
                           "passive_per_1000_words", "the_initial_pct",
                           "formulaic_total", "not_x_but_y",
                           "triads_per_1000_words"):
                    flag = "  <-- lower is better" if delta < 0 else ""
                print("%-32s %10s %10s %10s%s"
                      % (key, before, after, delta, flag))
        return 0

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for key, value in result.items():
            print("%-32s %s" % (key, value))
    return 0


if __name__ == "__main__":
    sys.exit(main())
