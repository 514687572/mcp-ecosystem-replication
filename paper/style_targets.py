"""List the sentences behind the style metrics, so they can be rewritten."""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ai_style_check import body_text, sentences, DEFAULT_TEX  # noqa: E402


def main():
    with io.open(DEFAULT_TEX, encoding="utf-8") as fh:
        tex = fh.read()
    tex = "\n".join(l for l in tex.splitlines()
                    if not l.lstrip().startswith("%"))
    text = body_text(tex)
    sents = sentences(text)

    passive = re.compile(
        r"\b(?:is|are|was|were|be|been|being)\s+\w+(?:ed|en)\b", re.I)
    print("=== sentences containing passive constructions (%d) ===" %
          sum(1 for s in sents if passive.search(s)))
    for s in sents:
        if passive.search(s):
            print("  -", s[:170])

    print("\n=== sentences opening with 'The' (%d) ===" %
          sum(1 for s in sents if re.match(r"The\b", s)))
    for s in sents:
        if re.match(r"The\b", s):
            print("  -", s[:150])


if __name__ == "__main__":
    main()
