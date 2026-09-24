"""GitHub enrichment for repositories that publish MCP servers.

Rate limits matter here. Without a token GitHub allows 60 core requests/hour
and 10 search requests/minute; with a read-only public token it is 5,000/hour.
Set the environment variable named in config (default GITHUB_TOKEN).

Every response is cached on disk, and the client tracks remaining quota so a run
stops cleanly rather than burning through a limit.
"""
import os
import re
import time
import urllib.parse

API = "https://api.github.com"

REPO_URL_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com[/:]([^/]+)/([^/#?]+)",
    re.IGNORECASE,
)


def parse_repo_url(url):
    """Return (owner, repo) for a GitHub URL, else (None, None)."""
    if not url:
        return None, None
    match = REPO_URL_RE.match(str(url).strip())
    if not match:
        return None, None
    owner, repo = match.group(1), match.group(2)
    if repo.endswith(".git"):
        repo = repo[:-4]
    return owner, repo


def token_from_env(cfg):
    return os.environ.get(cfg.get("github", {}).get("token_env_var", "GITHUB_TOKEN"))


def _headers(cfg):
    headers = {"Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    token = token_from_env(cfg)
    if token:
        headers["Authorization"] = "Bearer %s" % token
    return headers


class QuotaExhausted(RuntimeError):
    pass


def _call(session, cfg, path, params=None):
    """One GitHub API call with quota tracking."""
    url = path if path.startswith("http") else API + path
    payload = session.get_json(url, params=params, headers=_headers(cfg))
    # get_json hides headers, so probe the limit separately when it matters.
    return payload


def quota(session, cfg):
    """Current GitHub rate-limit state (one cheap request)."""
    import requests

    merged = {"User-Agent": session.user_agent}
    merged.update(_headers(cfg))
    try:
        response = requests.get(API + "/rate_limit", headers=merged, timeout=30)
        if response.status_code != 200:
            return None
        data = response.json().get("resources", {})
        return {
            "core_remaining": data.get("core", {}).get("remaining"),
            "core_limit": data.get("core", {}).get("limit"),
            "search_remaining": data.get("search", {}).get("remaining"),
            "search_limit": data.get("search", {}).get("limit"),
            "authenticated": bool(token_from_env(cfg)),
        }
    except Exception:  # noqa: BLE001
        return None


def search_repositories(session, cfg, query, per_page=100, max_pages=10):
    """Search repositories, paginating up to max_pages."""
    gh = cfg.get("github", {})
    per_page = int(gh.get("search_per_page", per_page))
    max_pages = int(gh.get("max_search_pages_per_query", max_pages))
    results = []
    for page in range(1, max_pages + 1):
        payload = _call(
            session, cfg, "/search/repositories",
            params={"q": query, "sort": "stars", "order": "desc",
                    "per_page": per_page, "page": page},
        )
        if "__http_error__" in payload:
            code = payload["__http_error__"]
            if code in (403, 429):
                raise QuotaExhausted("GitHub search rate limit hit on '%s'" % query)
            break
        items = payload.get("items") or []
        results.extend(items)
        if len(items) < per_page:
            break
        # Search API is limited to 10 requests/minute unauthenticated.
        time.sleep(7 if not token_from_env(cfg) else 0.5)
    return results


def repo_summary(repo):
    """Reduce a GitHub repository object to the fields the study needs."""
    owner = (repo.get("owner") or {}).get("login")
    license_info = repo.get("license") or {}
    return {
        "repo_full_name": repo.get("full_name"),
        "repo_owner": owner,
        "repo_name": repo.get("name"),
        "repo_url": repo.get("html_url"),
        "repo_description": repo.get("description"),
        "repo_stars": repo.get("stargazers_count"),
        "repo_forks": repo.get("forks_count"),
        "repo_watchers": repo.get("subscribers_count"),
        "repo_open_issues": repo.get("open_issues_count"),
        "repo_language": repo.get("language"),
        "repo_topics": "|".join(repo.get("topics") or []),
        "repo_license": license_info.get("spdx_id"),
        "repo_created_at": repo.get("created_at"),
        "repo_pushed_at": repo.get("pushed_at"),
        "repo_updated_at": repo.get("updated_at"),
        "repo_size_kb": repo.get("size"),
        "repo_is_fork": bool(repo.get("fork")),
        "repo_archived": bool(repo.get("archived")),
        "repo_has_issues": bool(repo.get("has_issues")),
        "repo_default_branch": repo.get("default_branch"),
    }


def get_repo(session, cfg, owner, name):
    payload = _call(session, cfg, "/repos/%s/%s" % (owner, name))
    if "__http_error__" in payload:
        return None
    return payload


def get_releases(session, cfg, owner, name, max_pages=2):
    releases = []
    for page in range(1, max_pages + 1):
        payload = _call(
            session, cfg, "/repos/%s/%s/releases" % (owner, name),
            params={"per_page": 100, "page": page},
        )
        if "__http_error__" in payload:
            break
        releases.extend(payload)
        if len(payload) < 100:
            break
    rows = []
    for rel in releases:
        rows.append(
            {
                "repo_full_name": "%s/%s" % (owner, name),
                "release_tag": rel.get("tag_name"),
                "release_name": rel.get("name"),
                "release_published_at": rel.get("published_at"),
                "release_prerelease": bool(rel.get("prerelease")),
                "release_draft": bool(rel.get("draft")),
                "release_assets": len(rel.get("assets") or []),
            }
        )
    return rows
