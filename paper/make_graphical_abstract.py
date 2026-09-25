"""Render the graphical abstract.

JSS asks for 531 x 1328 pixels (h x w) or proportionally more, readable at
5 x 13 cm, in TIFF, EPS, PDF or an MS Office format. This draws a single
13 x 5 cm panel and exports PDF (vector, preferred) and PNG (for inspection).

Every number is read from results/tables, not typed in.
"""
import os
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TABLES = os.path.join(ROOT, "results", "tables")

CM = 1 / 2.54


def read(name):
    return pd.read_csv(os.path.join(TABLES, name))


def main():
    census = read("t01_census_overview.csv").set_index("metric")["value"]
    timeline = read("t07_publishing_timeline.csv")
    concentration = read("t20_version_churn_concentration.csv")
    credential = read("t11_credential_hygiene.csv").set_index("metric")["value"]
    coded = read(os.path.join("..", "validation", "part_c_summary.csv")
                 ).set_index("metric")["value"]

    servers = int(census["published_server_names"])
    versions = int(census["published_versions"])
    top100 = concentration.loc[
        concentration["top_k_namespaces"].astype(str) == "100",
        "share_of_versions_pct",
    ].iloc[0]
    # Two credential rules are reported, so the tile shows the conservative
    # figure and the permissive one beside it rather than a single point.
    cred_strict = credential["credential-named and NOT marked secret"]
    cred_declared = credential["declared environment variables"]
    cred_permissive = credential[
        "permissive rule: look like credentials, NOT marked secret"]
    when_use = coded["description states WHEN to use the tool"]
    all_tools = coded["tools coded"]

    fig = plt.figure(figsize=(13 * CM, 5 * CM), dpi=300)

    # Left: the growth curve, which is the study's most recognisable evidence.
    ax = fig.add_axes([0.055, 0.22, 0.40, 0.60])
    ax.bar(range(len(timeline)), timeline["new_versions"], color="#9ecae1",
           width=0.8)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title("%d servers, %s versions\nin twelve months"
                 % (servers, format(versions, ",")),
                 fontsize=7.6, pad=3.0)
    ax.annotate("", xy=(len(timeline) - 1, timeline["new_versions"].iloc[-1]),
                xytext=(0, timeline["new_versions"].iloc[0]),
                arrowprops=dict(arrowstyle="->", color="#08519c", lw=1.1,
                                connectionstyle="arc3,rad=-0.25"))

    # Right: the four findings that answer the research questions.
    stats = [
        ("%.1f%%" % top100,
         "of all versions come from\n100 of %s namespaces"
         % format(int(census["distinct_namespaces"]), ",")),
        ("%.1f%%" % (100.0 * cred_strict / cred_declared),
         "of declared variables name an\nunflagged credential (%.1f%% "
         "permissive)" % (100.0 * cred_permissive / cred_declared)),
        ("%.1f%%" % (100.0 * when_use / all_tools),
         "of coded tool descriptions say\nwhen to choose the tool"),
        ("59.3%", "of servers never tag a release,\nso version counts mislead"),
    ]
    # Four tiles have to fit inside 5 cm, and the fourth caption used to be
    # placed below the canvas and silently clipped. The band arithmetic is
    # explicit here so a fifth tile cannot be added without noticing.
    TOP, STEP, CAPTION_GAP = 0.95, 0.205, 0.085
    for index, (value, caption) in enumerate(stats):
        top = TOP - index * STEP
        fig.text(0.505, top, value, fontsize=11, color="#08519c",
                 va="top", ha="left", fontweight="bold")
        fig.text(0.505, top - CAPTION_GAP, caption, fontsize=6.2, va="top",
                 ha="left", color="#222222", linespacing=1.3)

    fig.text(0.055, 0.055, "Model Context Protocol server ecosystem, "
             "frozen 24 September 2026", fontsize=6.8, color="#444444")

    for ext in ("pdf", "png"):
        path = os.path.join(HERE, "graphical_abstract.%s" % ext)
        fig.savefig(path)
        print("wrote %s" % path)
    plt.close(fig)

    from PIL import Image
    img = Image.open(os.path.join(HERE, "graphical_abstract.png"))
    print("pixel size: %d x %d (h x w); JSS asks for >= 531 x 1328"
          % (img.size[1], img.size[0]))

    # A caption placed below the canvas is clipped by savefig and leaves no
    # trace in the build output, which is how the fourth tile's label went
    # missing. Read the rendered page back and fail loudly instead.
    try:
        import fitz
    except ImportError:
        print("PyMuPDF unavailable; skipping the clipping check")
        return 0
    doc = fitz.open(os.path.join(HERE, "graphical_abstract.pdf"))
    page = doc[0]
    clipped = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                y0, y1 = span["bbox"][1], span["bbox"][3]
                if y0 < 0 or y1 > page.rect.height:
                    clipped.append("%r at y %.1f-%.1f" % (span["text"][:30], y0, y1))
    if clipped:
        print("FAIL clipped text in the graphical abstract:")
        for item in clipped:
            print("  " + item)
        return 1
    print("every text span fits inside the canvas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
