"""Harvest the official Model Context Protocol registry.

The registry at registry.modelcontextprotocol.io is the authoritative public
catalogue of published MCP servers. Each response page contains:

  servers[i].server   the published manifest (name, title, description, version,
                      repository, websiteUrl, packages[], remotes[], icons[])
  servers[i]._meta    registry bookkeeping (status, publishedAt, updatedAt,
                      statusChangedAt, isLatest)
  metadata.nextCursor opaque cursor for the next page

Note that the registry returns *every published version*, not just the newest
one, which is what makes the evolution analysis possible.

The harvest is resumable: progress is written to a cursor file after every page,
so an interrupted run continues where it stopped.
"""
import json
import os
import time

from . import config
from .http import CachedSession


def _official_meta(entry):
    return (entry.get("_meta") or {}).get(
        "io.modelcontextprotocol.registry/official", {}
    ) or {}


def harvest(cfg=None, session=None, limit_pages=None, verbose=True):
    """Download every registry page into data/raw/registry.jsonl.

    Returns a dict with counts and the paths written.
    """
    cfg = cfg or config.load()
    session = session or CachedSession(cfg)
    reg = cfg.get("registry", {})
    base_url = reg.get("base_url")
    page_limit = int(reg.get("page_limit", 100))
    max_pages = int(reg.get("max_pages", 400))
    if limit_pages is not None:
        max_pages = min(max_pages, int(limit_pages))

    config.ensure_dirs()
    jsonl_path = os.path.join(config.RAW_DIR, "registry.jsonl")
    cursor_path = os.path.join(config.INTERIM_DIR, "registry_cursor.json")

    cursor = None
    pages_done = 0
    entries = 0
    started = time.time()

    # A previous partial run appends rather than overwrites, so a resumed run
    # keeps everything already collected.
    resume = os.path.isfile(cursor_path)
    if resume:
        with open(cursor_path, encoding="utf-8") as fh:
            state = json.load(fh)
        cursor = state.get("next_cursor")
        pages_done = int(state.get("pages_done", 0))
        entries = int(state.get("entries", 0))
        if verbose:
            print("resuming: %d pages, %d entries already collected"
                  % (pages_done, entries))

    mode = "a" if resume else "w"
    with open(jsonl_path, mode, encoding="utf-8") as out:
        while pages_done < max_pages:
            params = {"limit": page_limit}
            if cursor:
                params["cursor"] = cursor
            # Registry pages are mutable while paginating, so bypass the cache
            # for the harvest itself; the cache still serves enrichment calls.
            payload = session.get_json(base_url, params=params, use_cache=False)

            page = payload.get("servers") or []
            for entry in page:
                out.write(json.dumps(entry, ensure_ascii=False) + "\n")
            out.flush()

            pages_done += 1
            entries += len(page)
            cursor = (payload.get("metadata") or {}).get("nextCursor")

            with open(cursor_path, "w", encoding="utf-8") as fh:
                json.dump(
                    {
                        "next_cursor": cursor,
                        "pages_done": pages_done,
                        "entries": entries,
                        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    },
                    fh,
                )

            if verbose:
                print("  page %-4d entries=%-6d cursor=%s"
                      % (pages_done, entries, "yes" if cursor else "end"))

            if not cursor or not page:
                break

    elapsed = time.time() - started
    result = {
        "pages": pages_done,
        "entries": entries,
        "complete": cursor is None,
        "raw_path": jsonl_path,
        "cursor_path": cursor_path,
        "elapsed_seconds": round(elapsed, 1),
        "http": session.summary(),
    }
    if verbose:
        print("harvest %s: %d entries over %d pages in %.1fs"
              % ("complete" if cursor is None else "partial",
                 entries, pages_done, elapsed))
    return result


def load_entries(path=None):
    """Read the harvested JSONL back into memory."""
    path = path or os.path.join(config.RAW_DIR, "registry.jsonl")
    records = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def flatten(entries):
    """Turn raw registry entries into flat dicts, one row per published version."""
    rows = []
    for entry in entries:
        server = entry.get("server") or {}
        meta = _official_meta(entry)
        packages = server.get("packages") or []
        remotes = server.get("remotes") or []
        repo = server.get("repository") or {}

        registry_types = sorted(
            {p.get("registryType") for p in packages if p.get("registryType")}
        )
        transport_set = {
            (p.get("transport") or {}).get("type") for p in packages
        }
        transport_set |= {r.get("type") for r in remotes}
        transports = sorted(t for t in transport_set if t)

        env_vars = []
        for p in packages:
            for var in p.get("environmentVariables") or []:
                env_vars.append(var)

        row = {
            "name": server.get("name"),
            "title": server.get("title"),
            "description": server.get("description"),
            "version": server.get("version"),
            "schema": server.get("$schema"),
            "repository_url": repo.get("url"),
            "repository_source": repo.get("source"),
            "website_url": server.get("websiteUrl"),
            "status": meta.get("status"),
            "is_latest": bool(meta.get("isLatest")),
            "published_at": meta.get("publishedAt"),
            "updated_at": meta.get("updatedAt"),
            "status_changed_at": meta.get("statusChangedAt"),
            "package_count": len(packages),
            "remote_count": len(remotes),
            "registry_types": "|".join(registry_types),
            "transports": "|".join(transports),
            "env_var_count": len(env_vars),
            "has_packages": bool(packages),
            "has_remotes": bool(remotes),
            "has_repository": bool(repo.get("url")),
            "has_website": bool(server.get("websiteUrl")),
        }
        rows.append(row)
    return rows


def latest_versions(rows):
    """Keep only the newest published version of each server name."""
    newest = {}
    for row in rows:
        name = row.get("name")
        if not name:
            continue
        current = newest.get(name)
        if current is None:
            newest[name] = row
            continue
        # Prefer the row flagged latest; fall back to the most recent timestamp.
        if row["is_latest"] and not current["is_latest"]:
            newest[name] = row
        elif row["is_latest"] == current["is_latest"]:
            if (row.get("published_at") or "") > (current.get("published_at") or ""):
                newest[name] = row
    return list(newest.values())


def extract_packages(entries):
    """One row per (server version, package) pair — the unit for supply-chain work."""
    rows = []
    for entry in entries:
        server = entry.get("server") or {}
        meta = _official_meta(entry)
        for package in server.get("packages") or []:
            transport = package.get("transport") or {}
            rows.append(
                {
                    "server_name": server.get("name"),
                    "server_version": server.get("version"),
                    "is_latest": bool(meta.get("isLatest")),
                    "status": meta.get("status"),
                    "published_at": meta.get("publishedAt"),
                    "registry_type": package.get("registryType"),
                    "registry_base_url": package.get("registryBaseUrl"),
                    "identifier": package.get("identifier"),
                    "package_version": package.get("version"),
                    "transport_type": transport.get("type"),
                    "transport_url": transport.get("url"),
                    "runtime_hint": package.get("runtimeHint"),
                    "has_runtime_args": bool(package.get("runtimeArguments")),
                    "has_package_args": bool(package.get("packageArguments")),
                }
            )
    return rows


def extract_environment_variables(entries):
    """One row per declared environment variable.

    This is the primary evidence base for the credential-handling part of the
    security analysis: what secrets a server asks the user to supply, whether
    they are flagged as secret, and whether they are marked required.
    """
    rows = []
    for entry in entries:
        server = entry.get("server") or {}
        meta = _official_meta(entry)
        for package in server.get("packages") or []:
            for var in package.get("environmentVariables") or []:
                rows.append(
                    {
                        "server_name": server.get("name"),
                        "server_version": server.get("version"),
                        "is_latest": bool(meta.get("isLatest")),
                        "registry_type": package.get("registryType"),
                        "identifier": package.get("identifier"),
                        "var_name": var.get("name"),
                        "var_description": var.get("description"),
                        "is_required": bool(var.get("isRequired")),
                        "is_secret": bool(var.get("isSecret")),
                        "default_value": var.get("default"),
                        "format": var.get("format"),
                        "choices": var.get("choices"),
                    }
                )
    return rows


def extract_remotes(entries):
    """One row per declared remote endpoint (the hosted-server surface)."""
    rows = []
    for entry in entries:
        server = entry.get("server") or {}
        meta = _official_meta(entry)
        for remote in server.get("remotes") or []:
            rows.append(
                {
                    "server_name": server.get("name"),
                    "server_version": server.get("version"),
                    "is_latest": bool(meta.get("isLatest")),
                    "remote_type": remote.get("type"),
                    "remote_url": remote.get("url"),
                }
            )
    return rows
