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
    tools = read("t21_tool_interface_summary.csv").set_index("metric")["value"]

    servers = int(census["published_server_names"])
    versions = int(census["published_versions"])
    top100 = concentration.loc[
        concentration["top_k_namespaces"].astype(str) == "100",
        "share_of_versions_pct",
    ].iloc[0]
    cred_unflagged = credential["credential-like but NOT marked secret"]
    cred_total = credential["variables that look like credentials"]
    when_use = tools["descriptions that state when to use the tool"]
    all_tools = tools["extracted tool definitions"]

    fig = plt.figure(figsize=(13 * CM, 5 * CM), dpi=300)

    # Left: the growth curve, which is the study's most recognisable evidence.
    ax = fig.add_axes([0.055, 0.20, 0.40, 0.66])
    ax.bar(range(len(timeline)), timeline["new_versions"], color="#9ecae1",
           width=0.8)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title("%d servers, %s versions\nin twelve months"
                 % (servers, format(versions, ",")),
                 fontsize=7.6, pad=3.5)
    ax.annotate("", xy=(len(timeline) - 1, timeline["new_versions"].iloc[-1]),
                xytext=(0, timeline["new_versions"].iloc[0]),
                arrowprops=dict(arrowstyle="->", color="#08519c", lw=1.1,
                                connectionstyle="arc3,rad=-0.25"))

    # Right: the four findings that answer the research questions.
    stats = [
        ("%.1f%%" % top100,
         "of all versions come from\n100 of %s namespaces"
         % format(int(census["distinct_namespaces"]), ",")),
        ("%.1f%%" % (100.0 * cred_unflagged / cred_total),
         "of credential-like variables\ncarry no secret flag"),
        ("%.1f%%" % (100.0 * when_use / all_tools),
         "of tool descriptions say when\nto choose the tool (strict read: 4%)"),
        ("59.3%", "of servers never tag a\nrelease, so version counts mislead"),
    ]
    top = 0.90
    for value, caption in stats:
        fig.text(0.505, top, value, fontsize=12, color="#08519c",
                 va="top", ha="left", fontweight="bold")
        fig.text(0.505, top - 0.215, caption, fontsize=6.4, va="top", ha="left",
                 color="#222222", linespacing=1.35)
        top -= 0.245

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
    return 0


if __name__ == "__main__":
    sys.exit(main())
