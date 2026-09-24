"""Step 3 — enrich registry packages with npm / PyPI facts.

Reads the harvested registry, collects every distinct (registryType, identifier)
pair, and asks the package registry for licence, deprecation, maintainer count,
download volume and publish history.

Writes incrementally to data/processed/package_enrichment.jsonl, so the job can
be interrupted and resumed without repeating work. The HTTP cache also makes
re-runs nearly free.

  python scripts/03_enrich_packages.py                 # latest versions only
  python scripts/03_enrich_packages.py --all           # every published version
  python scripts/03_enrich_packages.py --limit 200     # smoke test
"""
import argparse
import concurrent.futures
import json
import os
import sys
import time
import threading

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from mcpstudy import config, packages, registry  # noqa: E402
from mcpstudy.http import CachedSession  # noqa: E402


def load_done(path):
    done = set()
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    done.add((row.get("registry_type"), row.get("identifier")))
                except ValueError:
                    continue
    return done


def collect_targets(entries, latest_only=True, include=("npm", "pypi")):
    pairs = {}
    for row in registry.extract_packages(entries):
        if latest_only and not row.get("is_latest"):
            continue
        registry_type = row.get("registry_type")
        identifier = row.get("identifier")
        if not registry_type or not identifier:
            continue
        if registry_type not in include:
            continue
        key = (registry_type, identifier)
        if key not in pairs:
            pairs[key] = {
                "registry_type": registry_type,
                "identifier": identifier,
                "package_version": row.get("package_version"),
                "server_name": row.get("server_name"),
            }
    return list(pairs.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true",
                        help="enrich every published version, not just the latest")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--workers", type=int, default=8,
                        help="parallel workers; the per-host rate limiter still applies")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    cfg = config.load()
    session = CachedSession(cfg)
    out_path = config.out("package_enrichment.jsonl")
    done = load_done(out_path)
    entries = registry.load_entries()
    targets = collect_targets(entries, latest_only=not args.all)
    pending = [t for t in targets
               if (t["registry_type"], t["identifier"]) not in done]
    if args.limit:
        pending = pending[: args.limit]

    print("targets=%d  already done=%d  pending=%d"
          % (len(targets), len(done), len(pending)))
    if not pending:
        print("nothing to do")
        return

    started = time.time()
    write_lock = threading.Lock()
    counter = {"done": 0}

    def enrich(target, worker_session):
        row = dict(target)
        try:
            if target["registry_type"] == "npm":
                row.update(packages.npm_metadata(worker_session, target["identifier"]))
                row["npm_monthly_downloads"] = packages.npm_downloads(
                    worker_session, target["identifier"]
                )
            elif target["registry_type"] == "pypi":
                row.update(packages.pypi_metadata(worker_session, target["identifier"]))
        except Exception as exc:  # noqa: BLE001
            row["error"] = "%s: %s" % (type(exc).__name__, exc)
        return row

    # Each worker gets its own session (and therefore its own cache and limiter
    # state), which keeps the shared requests.Session out of thread-safety
    # trouble and lets the per-host pacing still hold per worker.
    workers = max(1, args.workers)
    # One reusable session per worker: each keeps its own thread-local state,
    # cache handle and pacing clock, so 8 workers do not corrupt a shared
    # requests.Session and each still paces itself politely.
    worker_sessions = [CachedSession(cfg) for _ in range(workers)]
    with open(out_path, "a", encoding="utf-8") as out:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {}
            for index, target in enumerate(pending):
                worker_session = worker_sessions[index % workers]
                futures[pool.submit(enrich, target, worker_session)] = target

            for future in concurrent.futures.as_completed(futures):
                target = futures[future]
                try:
                    row = future.result()
                except Exception as exc:  # noqa: BLE001
                    row = dict(target)
                    row["error"] = "%s: %s" % (type(exc).__name__, exc)
                with write_lock:
                    out.write(json.dumps(row, ensure_ascii=False) + "\n")
                    counter["done"] += 1
                    if counter["done"] % 25 == 0:
                        out.flush()
                        if not args.quiet:
                            elapsed = time.time() - started
                            rate = counter["done"] / elapsed if elapsed else 0
                            remaining = (len(pending) - counter["done"]) / rate if rate else 0
                            print("  %5d/%-5d  %.1f/s  eta %.0fs  %s"
                                  % (counter["done"], len(pending), rate, remaining,
                                     target["identifier"][:44]))
    print("wrote %s" % out_path)
    print("http: %s" % session.summary())


if __name__ == "__main__":
    main()
