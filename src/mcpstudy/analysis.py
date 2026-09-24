"""Turn harvested registry data into the tables the paper reports.

Every function returns a pandas DataFrame and, when run through
scripts/05_analyze.py, is written to results/tables/*.csv. The paper's claims
should be traceable to one of these tables.
"""
import re

import pandas as pd

CREDENTIAL_HINTS = (
    "token", "key", "secret", "password", "passwd", "credential",
    "api_key", "apikey", "auth", "oauth", "pat", "cookie", "session",
    "private", "access_key", "client_secret", "webhook", "dsn",
)


def _to_frame(rows, columns=None):
    frame = pd.DataFrame(rows)
    if frame.empty and columns:
        frame = pd.DataFrame(columns=columns)
    return frame


def _month(series):
    return pd.to_datetime(series, errors="coerce", utc=True).dt.strftime("%Y-%m")


def attach_version_counts(versions, latest):
    """Add a version_count column to the latest-version frame."""
    counts = (
        versions.groupby("name")
        .size()
        .rename("version_count")
        .reset_index()
    )
    enriched = latest.merge(counts, on="name", how="left")
    enriched["version_count"] = enriched["version_count"].fillna(1).astype(int)

    first_publish = (
        versions.assign(published_at=pd.to_datetime(
            versions["published_at"], errors="coerce", utc=True))
        .groupby("name")["published_at"]
        .min()
        .rename("first_published_at")
        .reset_index()
    )
    enriched = enriched.merge(first_publish, on="name", how="left")
    return enriched


# --- census ------------------------------------------------------------------


def census_overview(versions, latest):
    """Headline counts for the study."""

    def pct(part, whole):
        return round(100.0 * part / whole, 1) if whole else 0.0

    total_versions = len(versions)
    total_servers = len(latest)
    with_packages = int(latest["has_packages"].sum())
    with_remotes = int(latest["has_remotes"].sum())
    with_repo = int(latest["has_repository"].sum())
    deprecated = int((latest["status"] == "deprecated").sum())

    rows = [
        ("published_server_names", total_servers, 100.0),
        ("published_versions", total_versions, None),
        ("versions_per_server_mean", round(total_versions / total_servers, 2)
         if total_servers else 0, None),
        ("servers_with_packages", with_packages, pct(with_packages, total_servers)),
        ("servers_with_remote_endpoint", with_remotes, pct(with_remotes, total_servers)),
        ("servers_with_repository", with_repo, pct(with_repo, total_servers)),
        ("servers_deprecated", deprecated, pct(deprecated, total_servers)),
        ("distinct_namespaces", latest["name"].str.split("/").str[0].nunique(), None),
    ]
    return pd.DataFrame(rows, columns=["metric", "value", "share_of_servers_pct"])


def field_completeness(latest):
    """How often each optional manifest field is actually populated."""
    fields = [
        ("description", latest["description"].notna()),
        ("title", latest["title"].notna()),
        ("version", latest["version"].notna()),
        ("repository", latest["has_repository"]),
        ("websiteUrl", latest["has_website"]),
        ("packages", latest["has_packages"]),
        ("remotes", latest["has_remotes"]),
    ]
    total = len(latest)
    rows = []
    for name, mask in fields:
        present = int(mask.sum())
        rows.append(
            {
                "field": name,
                "present": present,
                "missing": total - present,
                "present_pct": round(100.0 * present / total, 1) if total else 0.0,
            }
        )
    return pd.DataFrame(rows).sort_values("present_pct", ascending=False)


def namespace_concentration(latest, top_n=25, min_servers=3):
    """Which organisations publish more than one server.

    The registry uses reverse-DNS names, so the namespace before the first dot
    is the publisher identity (for example io.github.acme/...).
    """
    frame = latest.copy()
    frame["namespace"] = frame["name"].str.split("/").str[0]
    grouped = (
        frame.groupby("namespace")
        .agg(servers=("name", "nunique"),
             versions=("version", "size"))
        .reset_index()
    )
    grouped["recurring"] = grouped["servers"] >= min_servers
    grouped = grouped.sort_values("servers", ascending=False)
    return grouped.head(top_n), grouped


def transport_distribution(versions):
    """Transport usage per published version."""
    frame = versions.copy()
    exploded = frame.assign(
        transport=frame["transports"].fillna("").str.split("|")
    ).explode("transport")
    exploded = exploded[exploded["transport"].astype(bool)]
    counts = (
        exploded.groupby("transport")
        .agg(versions=("name", "size"), servers=("name", "nunique"))
        .reset_index()
        .sort_values("versions", ascending=False)
    )
    counts["versions_pct"] = (
        100.0 * counts["versions"] / max(1, len(frame))
    ).round(1)
    return counts


def registry_type_distribution(packages):
    counts = (
        packages.groupby("registry_type")
        .agg(packages=("identifier", "size"),
             servers=("server_name", "nunique"))
        .reset_index()
        .sort_values("packages", ascending=False)
    )
    counts["packages_pct"] = (
        100.0 * counts["packages"] / max(1, len(packages))
    ).round(1)
    return counts


def publishing_timeline(versions, freq="M"):
    """New versions per month — the ecosystem growth curve."""
    frame = versions.copy()
    frame["month"] = _month(frame["published_at"])
    frame = frame.dropna(subset=["month"])
    by_version = (
        frame.groupby("month").agg(new_versions=("name", "size")).reset_index()
    )
    first_seen = (
        frame.sort_values("published_at")
        .groupby("name")["month"]
        .min()
        .value_counts()
        .sort_index()
        .rename("new_servers")
        .reset_index()
        .rename(columns={"index": "month"})
    )
    merged = by_version.merge(first_seen, on="month", how="outer").fillna(0)
    merged = merged.sort_values("month").reset_index(drop=True)
    merged["cumulative_servers"] = merged["new_servers"].cumsum()
    merged["cumulative_versions"] = merged["new_versions"].cumsum()
    return merged


def version_distribution(latest):
    """How many servers have how many versions — indicates maintenance activity."""
    frame = latest.copy()
    counts = frame["version_count"].value_counts().sort_index()
    table = counts.rename("servers").reset_index()
    table.columns = ["versions_published", "servers"]
    table["servers_pct"] = (100.0 * table["servers"] / max(1, len(frame))).round(1)
    return table


def schema_adoption(versions):
    frame = versions.copy()
    # Manifest $schema URLs look like
    #   https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json
    # The date segment identifies the protocol/schema revision.
    frame["schema_version"] = frame["schema"].fillna("").str.extract(
        r"/schemas/([0-9]{4}-[0-9]{2}-[0-9]{2})/", expand=False
    )
    frame["schema_version"] = frame["schema_version"].fillna("unknown")
    table = (
        frame.groupby("schema_version")
        .agg(versions=("name", "size"), servers=("name", "nunique"))
        .reset_index()
        .sort_values("versions", ascending=False)
    )
    table["versions_pct"] = (100.0 * table["versions"] / max(1, len(frame))).round(1)
    return table


# --- description quality -----------------------------------------------------


def description_quality(latest):
    """Cheap, reproducible proxies for manifest quality."""
    frame = latest.copy()
    desc = frame["description"].fillna("")
    frame["desc_len"] = desc.str.len()
    frame["desc_words"] = desc.str.split().str.len().fillna(0).astype(int)
    frame["desc_missing"] = frame["desc_len"] == 0
    frame["desc_title_duplicate"] = (
        desc.str.strip().str.lower()
        == frame["title"].fillna("").str.strip().str.lower()
    )
    # A description that is just the product name carries little routing signal.
    frame["desc_short"] = frame["desc_words"] < 5

    total = len(frame)
    summary = pd.DataFrame(
        [
            ("missing description", int(frame["desc_missing"].sum())),
            ("fewer than 5 words", int(frame["desc_short"].sum())),
            ("identical to title", int(frame["desc_title_duplicate"].sum())),
        ],
        columns=["issue", "servers"],
    )
    summary["servers_pct"] = (100.0 * summary["servers"] / max(1, total)).round(1)
    stats = pd.DataFrame(
        [
            ("description length (chars)", frame["desc_len"].mean()),
            ("description length p50", frame["desc_len"].median()),
            ("description length p90", frame["desc_len"].quantile(0.9)),
            ("description words (mean)", frame["desc_words"].mean()),
        ],
        columns=["statistic", "value"],
    )
    stats["value"] = stats["value"].round(1)
    return summary, stats, frame


# --- naming ------------------------------------------------------------------


def naming_conventions(latest):
    """How closely published names follow the reverse-DNS convention."""
    frame = latest.copy()
    name = frame["name"].fillna("")
    frame["has_namespace"] = name.str.contains("/")
    frame["namespace"] = name.str.split("/").str[0]
    frame["has_dot_in_namespace"] = frame["namespace"].str.contains(r"\.", regex=True)
    frame["server_part"] = name.str.split("/").str[-1]
    frame["server_part_has_upper"] = frame["server_part"].str.contains(r"[A-Z]", regex=True)
    frame["server_part_has_space"] = frame["server_part"].str.contains(" ")
    frame["server_part_has_underscore"] = frame["server_part"].str.contains("_")

    patterns = [
        ("no slash separator", ~frame["has_namespace"]),
        ("namespace without dot (not reverse-DNS)", frame["has_namespace"]
         & ~frame["has_dot_in_namespace"]),
        ("uppercase in server segment", frame["server_part_has_upper"]),
        ("space in server segment", frame["server_part_has_space"]),
        ("underscore in server segment", frame["server_part_has_underscore"]),
    ]
    total = len(frame)
    rows = []
    for label, mask in patterns:
        count = int(mask.sum())
        rows.append({"pattern": label, "servers": count,
                     "servers_pct": round(100.0 * count / max(1, total), 1)})
    return pd.DataFrame(rows), frame


# --- security ----------------------------------------------------------------


def credential_declarations(env_vars):
    """Credential hygiene across declared environment variables.

    The registry schema lets a publisher mark a variable as secret and/or
    required. Where a variable *looks* like a credential but is not marked
    secret, a client cannot know to redact it from logs or prompts.
    """
    if env_vars.empty:
        return pd.DataFrame(), pd.DataFrame()

    frame = env_vars.copy()
    name_lower = frame["var_name"].fillna("").str.lower()
    desc_lower = frame["var_description"].fillna("").str.lower()
    frame["looks_like_credential"] = (
        name_lower.apply(lambda v: any(h in v for h in CREDENTIAL_HINTS))
        | desc_lower.apply(lambda v: any(h in v for h in CREDENTIAL_HINTS))
    )

    total = len(frame)
    cred = frame[frame["looks_like_credential"]]
    summary = pd.DataFrame(
        [
            ("declared environment variables", total),
            ("required variables", int(frame["is_required"].sum())),
            ("variables marked secret", int(frame["is_secret"].sum())),
            ("variables that look like credentials", len(cred)),
            ("credential-like but NOT marked secret",
             int((~cred["is_secret"]).sum()) if len(cred) else 0),
            ("credential-like and required but NOT marked secret",
             int((cred["is_required"] & ~cred["is_secret"]).sum()) if len(cred) else 0),
            ("variables with a default value", int(frame["default_value"].notna().sum())),
            ("servers declaring at least one env var",
             frame["server_name"].nunique()),
            ("servers requiring at least one env var",
             frame.loc[frame["is_required"], "server_name"].nunique()),
        ],
        columns=["metric", "value"],
    )
    summary["share_pct"] = (100.0 * summary["value"] / max(1, total)).round(1)
    summary.loc[summary["metric"].str.startswith("servers"), "share_pct"] = None

    top_vars = (
        frame.groupby("var_name")
        .agg(declarations=("server_name", "size"),
             servers=("server_name", "nunique"),
             secret_flagged=("is_secret", "sum"))
        .reset_index()
        .sort_values("servers", ascending=False)
        .head(30)
    )
    top_vars["secret_flagged_pct"] = (
        100.0 * top_vars["secret_flagged"] / top_vars["declarations"]
    ).round(1)
    return summary, top_vars


def remote_endpoint_hygiene(remotes):
    """Scheme and host analysis for hosted (remote) servers."""
    if remotes.empty:
        return pd.DataFrame(), pd.DataFrame()
    frame = remotes.copy()
    url = frame["remote_url"].fillna("")
    frame["scheme"] = url.str.extract(r"^([a-zA-Z][a-zA-Z0-9+.-]*)://", expand=False)
    frame["host"] = url.str.extract(r"://([^/:]+)", expand=False)
    frame["is_plaintext"] = frame["scheme"].str.lower().eq("http")
    frame["host_is_ip"] = frame["host"].fillna("").str.match(r"^\d{1,3}(\.\d{1,3}){3}$")
    frame["host_is_localhost"] = frame["host"].fillna("").isin(
        ["localhost", "127.0.0.1", "0.0.0.0", "::1"]
    )

    total = len(frame)
    summary = pd.DataFrame(
        [
            ("remote endpoints", total),
            ("servers with a remote endpoint", frame["server_name"].nunique()),
            ("plaintext http endpoints", int(frame["is_plaintext"].sum())),
            ("endpoints on a bare IP address", int(frame["host_is_ip"].sum())),
            ("endpoints pointing at localhost", int(frame["host_is_localhost"].sum())),
            ("distinct hosts", frame["host"].nunique()),
        ],
        columns=["metric", "value"],
    )
    summary["share_pct"] = (100.0 * summary["value"] / max(1, total)).round(1)

    hosts = (
        frame.groupby("host")
        .agg(endpoints=("remote_url", "size"), servers=("server_name", "nunique"))
        .reset_index()
        .sort_values("servers", ascending=False)
        .head(30)
    )
    return summary, hosts


# --- evolution ---------------------------------------------------------------


def release_cadence(versions):
    """Time between consecutive published versions, per server."""
    frame = versions.copy()
    frame["published_at"] = pd.to_datetime(
        frame["published_at"], errors="coerce", utc=True
    )
    frame = frame.dropna(subset=["published_at", "name"])
    frame = frame.sort_values(["name", "published_at"])
    frame["prev_published_at"] = frame.groupby("name")["published_at"].shift(1)
    frame["gap_days"] = (
        frame["published_at"] - frame["prev_published_at"]
    ).dt.total_seconds() / 86400.0
    gaps = frame.dropna(subset=["gap_days"])
    if gaps.empty:
        return pd.DataFrame()
    stats = pd.DataFrame(
        [
            ("release-to-release gaps", len(gaps)),
            ("mean gap (days)", round(gaps["gap_days"].mean(), 1)),
            ("median gap (days)", round(gaps["gap_days"].median(), 1)),
            ("p90 gap (days)", round(gaps["gap_days"].quantile(0.9), 1)),
            ("gaps under 1 day", int((gaps["gap_days"] < 1).sum())),
            ("gaps over 180 days", int((gaps["gap_days"] > 180).sum())),
        ],
        columns=["statistic", "value"],
    )
    return stats


def staleness(latest, as_of):
    """How long since each server's most recent publish, relative to the freeze date."""
    frame = latest.copy()
    frame["last_published_at"] = pd.to_datetime(
        frame["published_at"], errors="coerce", utc=True
    )
    freeze = pd.Timestamp(as_of, tz="UTC")
    frame["days_since_publish"] = (
        (freeze - frame["last_published_at"]).dt.total_seconds() / 86400.0
    )

    single = frame["version_count"].fillna(1) <= 1
    days = frame["days_since_publish"]
    buckets = [
        ("single version, never updated again", single),
        ("multiple versions, last publish <= 30 days", ~single & (days <= 30)),
        ("multiple versions, 31-90 days", ~single & (days > 30) & (days <= 90)),
        ("multiple versions, 91-180 days", ~single & (days > 90) & (days <= 180)),
        ("multiple versions, 181-365 days", ~single & (days > 180) & (days <= 365)),
        ("multiple versions, > 365 days", ~single & (days > 365)),
    ]
    rows = []
    total = len(frame)
    for label, mask in buckets:
        count = int(mask.sum())
        rows.append({"bucket": label, "servers": count,
                     "servers_pct": round(100.0 * count / max(1, total), 1)})
    return pd.DataFrame(rows), frame


def deprecations(versions):
    """Which servers have been withdrawn, and how quickly."""
    frame = versions.copy()
    frame = frame[frame["status"].notna()]
    latest_flag = frame[frame["is_latest"]]
    deprecated = latest_flag[latest_flag["status"] == "deprecated"]
    rows = []
    for _, row in deprecated.iterrows():
        rows.append(
            {
                "server_name": row["name"],
                "last_version": row["version"],
                "published_at": row["published_at"],
                "status_changed_at": row.get("status_changed_at"),
                "versions_published": row.get("version_count"),
            }
        )
    return _to_frame(rows, columns=["server_name", "last_version", "published_at",
                                    "status_changed_at", "versions_published"])


def version_churn_concentration(versions):
    """How concentrated is publishing activity across namespaces?

    A small number of namespaces publish hundreds of versions each. Because
    "versions published" is the most tempting proxy for ecosystem activity,
    the concentration has to be quantified before that proxy is used.
    """
    frame = versions.copy()
    frame["namespace"] = frame["name"].fillna("").str.split("/").str[0]
    counts = frame.groupby("namespace").size().sort_values(ascending=False)
    total = int(counts.sum())
    if total == 0:
        return pd.DataFrame(), counts

    rows = []
    for k in (1, 5, 10, 25, 50, 100):
        top = int(counts.head(k).sum())
        rows.append(
            {
                "top_k_namespaces": k,
                "versions": top,
                "share_of_versions_pct": round(100.0 * top / total, 1),
            }
        )
    # Shares among the bottom half of namespaces, for contrast.
    half = max(1, len(counts) // 2)
    rows.append(
        {
            "top_k_namespaces": "bottom 50%% of namespaces (%d)" % half,
            "versions": int(counts.tail(half).sum()),
            "share_of_versions_pct": round(
                100.0 * counts.tail(half).sum() / total, 1
            ),
        }
    )
    return pd.DataFrame(rows), counts


def tool_interface_profile(tools):
    """What the extracted tool definitions say about interface design (RQ1)."""
    if tools.empty:
        return pd.DataFrame(), pd.DataFrame()

    frame = tools.copy()
    frame["desc_len"] = frame["tool_description"].fillna("").str.len()
    frame["desc_words"] = frame["tool_description"].fillna("").str.split().str.len()
    name = frame["tool_name"].fillna("")
    frame["name_len"] = name.str.len()
    frame["has_underscore"] = name.str.contains("_")
    frame["has_camel"] = name.str.contains(r"[a-z][A-Z]")
    frame["has_dash"] = name.str.contains("-")
    frame["has_verb_noun"] = name.str.match(r"^[a-z]+[_\-][a-z]")
    frame["desc_has_when_to_use"] = (
        frame["tool_description"].fillna("").str.lower()
        .str.contains(r"use (?:this|when)|when to use|use it when", regex=True)
    )
    frame["desc_is_short"] = frame["desc_words"] < 5

    total = len(frame)
    summary = pd.DataFrame(
        [
            ("extracted tool definitions", total),
            ("servers represented", frame["server_name"].nunique()),
            ("tools per server (mean)",
             round(total / max(1, frame["server_name"].nunique()), 1)),
            ("tools with a description", int((frame["desc_len"] > 0).sum())),
            ("descriptions under 5 words", int(frame["desc_is_short"].sum())),
            ("descriptions that state when to use the tool",
             int(frame["desc_has_when_to_use"].sum())),
            ("tools declaring an input schema", int(frame["has_schema"].sum())),
            ("snake_case names", int(frame["has_underscore"].sum())),
            ("camelCase names", int(frame["has_camel"].sum())),
            ("kebab-case names", int(frame["has_dash"].sum())),
        ],
        columns=["metric", "value"],
    )
    summary["share_pct"] = (100.0 * summary["value"] / max(1, total)).round(1)
    summary.loc[
        summary["metric"].isin(["extracted tool definitions", "servers represented",
                                "tools per server (mean)"]),
        "share_pct",
    ] = None

    per_server = (
        frame.groupby("server_name")
        .agg(tools=("tool_name", "size"),
             with_description=("desc_len", lambda s: int((s > 0).sum())),
             with_schema=("has_schema", "sum"),
             mean_desc_words=("desc_words", "mean"))
        .reset_index()
        .sort_values("tools", ascending=False)
    )
    per_server["mean_desc_words"] = per_server["mean_desc_words"].round(1)
    return summary, per_server


def package_profile(enrichment):
    """Licence, maintenance and adoption facts for published packages."""
    if enrichment.empty:
        return pd.DataFrame(), pd.DataFrame()

    frame = enrichment.copy()
    npm = frame[frame["registry_type"] == "npm"]
    pypi = frame[frame["registry_type"] == "pypi"]

    rows = []
    rows.append(("packages enriched", len(frame)))
    rows.append(("npm packages", len(npm)))
    rows.append(("PyPI packages", len(pypi)))
    if len(npm) and "npm_license" in npm.columns:
        rows.append(("npm: with a licence declared",
                     int(npm["npm_license"].notna().sum())))
        rows.append(("npm: deprecated", int(npm["npm_deprecated"].fillna(False).sum())))
        rows.append(("npm: single maintainer",
                     int((npm["npm_maintainer_count"] == 1).sum())))
        rows.append(("npm: no maintainer recorded",
                     int(npm["npm_maintainer_count"].fillna(0).eq(0).sum())))
        rows.append(("npm: median versions published",
                     float(npm["npm_version_count"].median())))
        rows.append(("npm: median monthly downloads",
                     float(npm["npm_monthly_downloads"].dropna().median())
                     if npm["npm_monthly_downloads"].notna().any() else 0.0))
        rows.append(("npm: zero downloads in last month",
                     int(npm["npm_monthly_downloads"].fillna(0).eq(0).sum())))
    if len(pypi) and "pypi_license" in pypi.columns:
        rows.append(("PyPI: with a licence declared",
                     int(pypi["pypi_license"].notna().sum())))
        rows.append(("PyPI: yanked releases", int(pypi["pypi_yanked"].fillna(False).sum())))

    summary = pd.DataFrame(rows, columns=["metric", "value"])
    summary["share_pct"] = (
        100.0 * summary["value"] / max(1, len(frame))
    ).round(1)

    licence_frames = []
    for label, sub, column in (("npm", npm, "npm_license"),
                               ("pypi", pypi, "pypi_license")):
        if column in sub.columns and sub[column].notna().any():
            counts = sub[column].value_counts().rename("count").reset_index()
            counts.columns = ["licence", "count"]
            counts["registry"] = label
            licence_frames.append(counts)
    licences = (
        pd.concat(licence_frames, ignore_index=True).head(20)
        if licence_frames else pd.DataFrame(columns=["licence", "count", "registry"])
    )
    return summary, licences


def github_profile(repos):
    """Repository health for servers that publish their source."""
    if repos.empty:
        return pd.DataFrame(), pd.DataFrame()
    frame = repos[repos.get("status") == "ok"].copy() if "status" in repos else repos.copy()
    if frame.empty:
        return pd.DataFrame(), pd.DataFrame()
    frame["repo_created_at"] = pd.to_datetime(
        frame["repo_created_at"], errors="coerce", utc=True
    )
    frame["repo_pushed_at"] = pd.to_datetime(
        frame["repo_pushed_at"], errors="coerce", utc=True
    )
    frame["age_days"] = (
        pd.Timestamp.now(tz="UTC") - frame["repo_created_at"]
    ).dt.total_seconds() / 86400.0
    frame["days_since_push"] = (
        pd.Timestamp.now(tz="UTC") - frame["repo_pushed_at"]
    ).dt.total_seconds() / 86400.0

    rows = [
        ("repositories resolved", len(frame)),
        ("no licence declared", int(frame["repo_license"].fillna("NOASSERTION")
                                    .isin(["NOASSERTION", "NONE", ""]).sum())),
        ("archived", int(frame["repo_archived"].fillna(False).sum())),
        ("forks", int(frame["repo_is_fork"].fillna(False).sum())),
        ("with no stars", int(frame["repo_stars"].fillna(0).eq(0).sum())),
        ("with >= 100 stars", int(frame["repo_stars"].fillna(0).ge(100).sum())),
        ("no push in 180 days", int(frame["days_since_push"].gt(180).sum())),
        ("median stars", float(frame["repo_stars"].median() or 0)),
        ("median age (days)", round(float(frame["age_days"].median() or 0), 0)),
    ]
    summary = pd.DataFrame(rows, columns=["metric", "value"])
    summary["share_pct"] = (100.0 * summary["value"] / max(1, len(frame))).round(1)
    summary.loc[
        summary["metric"].isin(["median stars", "median age (days)"]),
        "share_pct",
    ] = None

    by_language = (
        frame.groupby("repo_language")
        .agg(repos=("repo_full_name", "size"),
             median_stars=("repo_stars", "median"))
        .reset_index()
        .sort_values("repos", ascending=False)
        .head(15)
    )
    return summary, by_language


def cross_source_signals(versions, latest):
    """Do manifest properties predict publishing activity?

    Reported as associations, not causes. Every comparison is group medians so
    a handful of hyper-publishers cannot dominate the result.
    """
    frame = latest.copy()
    rows = []
    for label, mask in [
        ("declares a repository", frame["has_repository"]),
        ("does not declare a repository", ~frame["has_repository"]),
        ("ships a package", frame["has_packages"]),
        ("hosted only (no package)", ~frame["has_packages"]),
        ("has a title", frame["title"].notna()),
        ("has no title", frame["title"].isna()),
    ]:
        subset = frame[mask]
        rows.append(
            {
                "group": label,
                "servers": len(subset),
                "median_versions": float(subset["version_count"].median())
                if len(subset) else 0.0,
                "mean_versions": round(float(subset["version_count"].mean()), 2)
                if len(subset) else 0.0,
                "share_deprecated_pct": round(
                    100.0 * (subset["status"] == "deprecated").mean(), 1
                ) if len(subset) else 0.0,
            }
        )
    return pd.DataFrame(rows)
