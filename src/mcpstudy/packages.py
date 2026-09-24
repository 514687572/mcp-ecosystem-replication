"""Enrich registry entries with package-registry facts (npm and PyPI).

The MCP registry tells us which package implements a server; these calls add the
things the registry does not carry: deprecation flags, licence, maintainer count,
download volume, publish history and dependency declarations. All of it is
public and needs no credentials.

Keep the call volume in mind: one npm package can cost two requests (metadata +
downloads). The on-disk cache means re-runs are free.
"""
import json
import os
import tarfile
import urllib.parse

from . import config


def _safe(name):
    """URL-quote a package name while keeping the npm scope prefix readable."""
    return urllib.parse.quote(str(name), safe="@")


def npm_metadata(session, name):
    """Registry metadata for an npm package, or an error marker."""
    url = "%s/%s" % (session.cfg["packages"]["npm_registry"], _safe(name))
    payload = session.get_json(url)
    if "__http_error__" in payload:
        return {"__error__": payload["__http_error__"]}
    latest = payload.get("dist-tags", {}).get("latest")
    versions = payload.get("versions") or {}
    version_meta = versions.get(latest) or {}
    times = payload.get("time") or {}
    maintainers = payload.get("maintainers") or []
    if isinstance(maintainers, dict):
        maintainers = [maintainers]
    return {
        "npm_name": payload.get("name"),
        "npm_latest_version": latest,
        "npm_created": times.get("created"),
        "npm_modified": times.get("modified"),
        "npm_version_count": len(versions),
        "npm_license": version_meta.get("license") or payload.get("license"),
        "npm_deprecated": bool(version_meta.get("deprecated")),
        "npm_maintainer_count": len(maintainers),
        "npm_has_repository": bool(
            (version_meta.get("repository") or {}).get("url")
            if isinstance(version_meta.get("repository"), dict)
            else version_meta.get("repository")
        ),
        "npm_dependencies": len(version_meta.get("dependencies") or {}),
        "npm_dev_dependencies": len(version_meta.get("devDependencies") or {}),
        "npm_scripts": "|".join(sorted((version_meta.get("scripts") or {}).keys())),
        "npm_tarball": (version_meta.get("dist") or {}).get("tarball"),
    }


def npm_downloads(session, name, period="last-month"):
    # The configured endpoint already carries the period suffix
    # (for example .../downloads/point/last-month).
    base = session.cfg["packages"]["npm_downloads"].rstrip("/")
    url = "%s/%s" % (base, _safe(name))
    payload = session.get_json(url)
    if "__http_error__" in payload:
        return None
    return payload.get("downloads")


def pypi_metadata(session, name):
    """PyPI JSON metadata for a package, or an error marker."""
    url = "%s/%s/json" % (session.cfg["packages"]["pypi_json"], _safe(name))
    payload = session.get_json(url)
    if "__http_error__" in payload:
        return {"__error__": payload["__http_error__"]}
    info = payload.get("info") or {}
    releases = payload.get("releases") or {}
    urls = info.get("project_urls") or {}
    return {
        "pypi_name": info.get("name"),
        "pypi_latest_version": info.get("version"),
        "pypi_summary": info.get("summary"),
        "pypi_license": info.get("license"),
        "pypi_requires_python": info.get("requires_python"),
        "pypi_release_count": len(releases),
        "pypi_author": info.get("author"),
        "pypi_project_urls": "|".join(sorted(urls.keys())) if isinstance(urls, dict) else "",
        "pypi_requires_dist": len(info.get("requires_dist") or []),
        "pypi_yanked": any(
            f.get("yanked")
            for files in releases.values()
            for f in (files or [])
        ),
    }


# --- source archives ---------------------------------------------------------


def download_npm_tarball(session, tarball_url, dest_dir):
    """Fetch and extract an npm tarball; returns the extraction directory."""
    if not tarball_url:
        return None
    os.makedirs(dest_dir, exist_ok=True)
    archive = os.path.join(dest_dir, "package.tgz")
    if not os.path.isfile(archive):
        with open(archive, "wb") as fh:
            fh.write(session.get_bytes(tarball_url))
    extract_to = os.path.join(dest_dir, "package")
    if not os.path.isdir(extract_to):
        with tarfile.open(archive, "r:gz") as tar:
            _safe_extract(tar, dest_dir)
    return extract_to if os.path.isdir(extract_to) else dest_dir


def download_pypi_sdist(session, name, version, dest_dir):
    """Fetch and extract a PyPI source distribution; returns the directory."""
    url = "%s/%s/%s/json" % (session.cfg["packages"]["pypi_json"], _safe(name), version)
    payload = session.get_json(url)
    if "__http_error__" in payload:
        return None
    files = payload.get("urls") or []
    sdist = next(
        (f for f in files if f.get("packagetype") == "sdist"),
        files[0] if files else None,
    )
    if not sdist:
        return None
    os.makedirs(dest_dir, exist_ok=True)
    archive = os.path.join(dest_dir, os.path.basename(sdist["url"]))
    if not os.path.isfile(archive):
        with open(archive, "wb") as fh:
            fh.write(session.get_bytes(sdist["url"]))
    extract_to = os.path.join(dest_dir, "src")
    if not os.path.isdir(extract_to):
        os.makedirs(extract_to, exist_ok=True)
        try:
            with tarfile.open(archive, "r:*") as tar:
                _safe_extract(tar, extract_to)
        except tarfile.TarError:
            return None
    return extract_to


def _safe_extract(tar, dest):
    """Extract while refusing entries that escape the destination directory."""
    dest_abs = os.path.abspath(dest)
    for member in tar.getmembers():
        target = os.path.abspath(os.path.join(dest_abs, member.name))
        if not target.startswith(dest_abs + os.sep) and target != dest_abs:
            raise ValueError("refusing unsafe archive member: %s" % member.name)
    tar.extractall(dest_abs)


def write_json(name, payload):
    path = os.path.join(config.PROCESSED_DIR, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    return path
