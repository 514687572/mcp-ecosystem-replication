"""Check the rendered PDF for text that falls outside the printable area.

The LaTeX log reports overfull boxes, but those include invisible assembly
boxes that the CAS class creates on the title page, and they say nothing about
whether a table or figure actually escapes its column. This inspects the
rendered pages instead: for every text span it compares the bounding box
against the page's own content area.

Run: python paper/check_layout.py
"""
import os
import sys

import fitz  # PyMuPDF

HERE = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(HERE, "latex", "mcp-ecosystem.pdf")

# A4 is 595 x 842 pt. The CAS layout keeps roughly 40 pt of side margin, but
# the running head and footer sit deliberately closer to the edge, so the
# vertical check excludes that band rather than reporting it as overflow.
MARGIN = 30.0
HEADER_FOOTER_BAND = 52.0


def main():
    if not os.path.isfile(PDF):
        print("no PDF at %s" % PDF)
        return 2
    doc = fitz.open(PDF)
    print("pages: %d" % doc.page_count)

    worst = []
    out_of_bounds = []
    for page_index, page in enumerate(doc, 1):
        rect = page.rect
        left_limit = rect.x0 + MARGIN
        right_limit = rect.x1 - MARGIN

        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    x0, y0, x1, y1 = span["bbox"]
                    # Skip the running head and footer, which are outside the
                    # body block by design.
                    if (y1 < rect.y0 + HEADER_FOOTER_BAND
                            or y0 > rect.y1 - HEADER_FOOTER_BAND):
                        continue
                    overflow = max(left_limit - x0, x1 - right_limit)
                    if overflow > 0:
                        out_of_bounds.append(
                            (overflow, page_index, span["text"][:60].strip()))
                    elif x1 > right_limit - 6:
                        worst.append((right_limit - x1, page_index,
                                      span["text"][:60].strip()))

    if out_of_bounds:
        print("\ntext outside the printable area:")
        for overflow, page, text in sorted(out_of_bounds, reverse=True)[:12]:
            print("  page %-3d %5.1f pt over  %s" % (page, overflow, text))
    else:
        print("no text outside a %.0f pt margin on any page" % MARGIN)

    print("\nspans ending within 6 pt of the right margin: %d" % len(worst))
    for remaining, page, text in sorted(worst)[:5]:
        print("  page %-3d %4.1f pt from margin  %s" % (page, remaining, text))
    return 1 if out_of_bounds else 0


if __name__ == "__main__":
    sys.exit(main())
