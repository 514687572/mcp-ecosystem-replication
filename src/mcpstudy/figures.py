"""Publication figures for the MCP ecosystem study.

Each figure is written as both PNG (for quick inspection) and PDF (vector, for
submission). Captions are returned by make_all so the paper can reuse them
verbatim.
"""
import os

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

plt.rcParams.update(
    {
        "figure.dpi": 140,
        "savefig.bbox": "tight",
        "font.size": 9,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


def _save(fig, name, figures_dir):
    os.makedirs(figures_dir, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(figures_dir, "%s.%s" % (name, ext)))
    plt.close(fig)
    print("  figure %-38s" % ("%s.png/.pdf" % name))


def ecosystem_growth(timeline, figures_dir):
    """Cumulative server count and monthly new versions."""
    frame = timeline.copy()
    frame = frame[frame["month"].notna()]
    if frame.empty:
        return
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    ax.bar(frame["month"], frame["new_versions"], color="#9ecae1",
           label="new versions published")
    ax.set_ylabel("new versions / month")
    ax.set_xlabel("month")
    ax2 = ax.twinx()
    ax2.plot(frame["month"], frame["cumulative_servers"], color="#08519c",
             marker="o", markersize=3, label="cumulative servers")
    ax2.set_ylabel("cumulative distinct servers")
    ax2.grid(False)
    step = max(1, len(frame) // 12)
    ax.set_xticks(list(range(0, len(frame), step)))
    ax.set_xticklabels(frame["month"].iloc[::step], rotation=45, ha="right")
    lines = ax.get_legend_handles_labels()[0] + ax2.get_legend_handles_labels()[0]
    labels = ax.get_legend_handles_labels()[1] + ax2.get_legend_handles_labels()[1]
    ax.legend(lines, labels, loc="upper left", frameon=False, fontsize=8)
    _save(fig, "fig1_ecosystem_growth", figures_dir)


def version_churn(latest, figures_dir):
    """Distribution of how many versions each server has published."""
    if "version_count" not in latest:
        return
    counts = latest["version_count"].value_counts().sort_index()
    capped = counts[counts.index <= 20]
    overflow = int(counts[counts.index > 20].sum()) if (counts.index > 20).any() else 0
    if overflow:
        capped = pd.concat([capped, pd.Series({21: overflow})])
    fig, ax = plt.subplots(figsize=(5.2, 3.0))
    ax.bar(capped.index.astype(int), capped.values, color="#6baed6")
    ax.set_xlabel("published versions per server (21 = 21+)")
    ax.set_ylabel("servers")
    ax.set_xticks(range(1, 22, 2))
    _save(fig, "fig2_version_churn", figures_dir)


def credential_hygiene(env_vars, figures_dir):
    """How often credential-like variables are flagged as secret."""
    if env_vars.empty:
        return
    from .analysis import CREDENTIAL_HINTS

    frame = env_vars
    if "looks_like_credential" not in frame.columns:
        name_lower = frame["var_name"].fillna("").str.lower()
        desc_lower = frame["var_description"].fillna("").str.lower()
        frame = frame.assign(
            looks_like_credential=name_lower.apply(
                lambda v: any(h in v for h in CREDENTIAL_HINTS)
            )
            | desc_lower.apply(lambda v: any(h in v for h in CREDENTIAL_HINTS))
        )
    cred = frame[frame["looks_like_credential"]]
    if cred.empty:
        return
    groups = [
        ("flagged secret", int(cred["is_secret"].sum())),
        ("not flagged secret", int((~cred["is_secret"]).sum())),
    ]
    fig, ax = plt.subplots(figsize=(4.6, 2.8))
    ax.bar([g[0] for g in groups], [g[1] for g in groups],
           color=["#31a354", "#de2d26"])
    ax.set_ylabel("credential-like variables")
    for i, (_, value) in enumerate(groups):
        ax.text(i, value, str(value), ha="center", va="bottom", fontsize=8)
    _save(fig, "fig3_credential_flagging", figures_dir)


def transport_mix(remotes, versions, figures_dir):
    """Endpoint type mix for hosted servers."""
    if remotes.empty:
        return
    counts = remotes["remote_type"].value_counts()
    fig, ax = plt.subplots(figsize=(4.6, 2.8))
    ax.bar(counts.index.astype(str), counts.values, color="#756bb1")
    ax.set_ylabel("remote endpoints")
    ax.set_xlabel("transport type")
    _save(fig, "fig4_remote_transports", figures_dir)


def make_all(timeline, latest, env_vars, remotes, figures_dir):
    ecosystem_growth(timeline, figures_dir)
    version_churn(latest, figures_dir)
    credential_hygiene(env_vars, figures_dir)
    transport_mix(remotes, latest, figures_dir)
