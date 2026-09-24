"""Step 4 — download package sources and extract MCP tool definitions.

Cluster-level analysis of *what tools servers expose* has to read the
implementation, because tool definitions live in code rather than in the
registry manifest. This step downloads npm tarballs and PyPI source
distributions, scans them, and records every tool registration it can find.

Downloading every package would be tens of gigabytes, so the study works on a
random sample drawn with a fixed seed. The seed and the sampling rule are part
of the method, and the sample is reproducible from the harvested registry alone.

  python scripts/04_extract_tools.py --sample 1200 --seed 20260924
  python scripts/04_extract_tools.py --sample 40 --seed 1   # smoke test
"""
import argparse
import concurrent.futures
import json
import os
import random
import shutil
import sys
import time
import threading

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from mcpstudy import config, packages, registry, tools_extract  # noqa: E402
from mcpstudy.http import CachedSession  # noqa: E402

WORK_DIR_NAME = "package_sources"


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
                    done.add(row.get("key"))
                except ValueError:
                    continue
    return done


def build_targets(entries, session, cfg):
    """Resolve latest-version npm/pypi packages into downloadable targets."""
    targets = []
    seen = set()
    for row in registry.extract_packages(entries):
        if not row.get("is_latest"):
            continue
        registry_type = row.get("registry_type")
        identifier = row.get("identifier")
        if registry_type not in ("npm", "pypi") or not identifier:
            continue
        key = "%s:%s" % (registry_type, identifier)
        if key in seen:
            continue
        seen.add(key)
        targets.append(
            {
                "key": key,
                "registry_type": registry_type,
                "identifier": identifier,
                "server_name": row.get("server_name"),
            }
        )
    return targets


def resolve_download(session, target):
    """Work out the archive URL for a target without downloading the archive."""
    if target["registry_type"] == "npm":
        meta = packages.npm_metadata(session, target["identifier"])
        if meta.get("__error__"):
            return None, meta["__error__"]
        return {"url": meta.get("npm_tarball"), "kind": "npm"}, None
    name = target["identifier"]
    url = "%s/%s/json" % (session.cfg["packages"]["pypi_json"],
                          packages._safe(name))
    payload = session.get_json(url)
    if "__http_error__" in payload:
        return None, payload["__http_error__"]
    version = (payload.get("info") or {}).get("version")
    return {"url": None, "kind": "pypi", "name": name, "version": version}, None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=int, default=1200,
                        help="number of packages to draw from the population")
    parser.add_argument("--seed", type=int, default=20260924)
    parser.add_argument("--limit", type=int, default=None,
                        help="hard cap on packages actually processed this run")
    parser.add_argument("--keep-sources", action="store_true",
                        help="do not delete extracted sources after parsing")
    parser.add_argument("--workers", type=int, default=6,
                        help="parallel download+parse workers")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    cfg = config.load()
    session = CachedSession(cfg)
    entries = registry.load_entries()
    targets = build_targets(entries, session, cfg)
    print("latest-version npm/pypi packages available: %d" % len(targets))

    # Reproducible sample: sort first so the draw does not depend on file order.
    targets.sort(key=lambda t: t["key"])
    sample_size = min(args.sample, len(targets))
    rng = random.Random(args.seed)
    sample = rng.sample(targets, sample_size)
    sample_keys = {t["key"] for t in sample}

    # Persist the drawn sample so the paper can state exactly what was analysed.
    sample_path = os.path.join(config.INTERIM_DIR, "tool_sample.json")
    with open(sample_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "seed": args.seed,
                "population_size": len(targets),
                "sample_size": sample_size,
                "keys": sorted(sample_keys),
            },
            fh,
            indent=1,
        )
    print("sample: %d packages, seed %d -> %s"
          % (sample_size, args.seed, sample_path))

    tools_path = config.out("tools.jsonl")
    coverage_path = config.out("tool_extraction_coverage.jsonl")
    done = load_done(coverage_path)
    pending = [t for t in sample if t["key"] not in done]
    if args.limit:
        pending = pending[: args.limit]
    print("already processed: %d   pending this run: %d" % (len(done), len(pending)))
    if not pending:
        print("nothing to do")
        return

    work_root = os.path.join(config.DATA_DIR, WORK_DIR_NAME)
    os.makedirs(work_root, exist_ok=True)
    started = time.time()
    write_lock = threading.Lock()
    counter = {"done": 0}
    workers = max(1, args.workers)
    worker_sessions = [CachedSession(cfg) for _ in range(workers)]

    def process(target, session):
        """Download a package source and extract what it declares."""
        row = dict(target)
        records = []
        dest = os.path.join(work_root, target["key"].replace(":", "__")
                            .replace("/", "_"))
        try:
            resolved, error = resolve_download(session, target)
            if error:
                row["status"] = "metadata_error"
                row["error"] = str(error)
            elif resolved["kind"] == "npm":
                root = packages.download_npm_tarball(session, resolved["url"], dest)
                records, scanned = tools_extract.extract_from_package(
                    root, target["server_name"], target["registry_type"]
                )
                row["files_scanned"] = scanned
                row["status"] = "ok"
            else:
                root = packages.download_pypi_sdist(
                    session, resolved["name"], resolved["version"], dest
                )
                if root is None:
                    row["status"] = "no_sdist"
                else:
                    records, scanned = tools_extract.extract_from_package(
                        root, target["server_name"], target["registry_type"]
                    )
                    row["files_scanned"] = scanned
                    row["status"] = "ok"
        except Exception as exc:  # noqa: BLE001
            row["status"] = "error"
            row["error"] = "%s: %s" % (type(exc).__name__, exc)
        records = tools_extract.dedupe_tools(records)
        for record in records:
            record["package_key"] = target["key"]
        if not args.keep_sources:
            shutil.rmtree(dest, ignore_errors=True)
        row["tools_found"] = len(records)
        return row, records

    with open(coverage_path, "a", encoding="utf-8") as cov, \
            open(tools_path, "a", encoding="utf-8") as out:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {}
            for index, target in enumerate(pending):
                futures[pool.submit(process, target,
                                    worker_sessions[index % workers])] = target
            for future in concurrent.futures.as_completed(futures):
                target = futures[future]
                try:
                    row, records = future.result()
                except Exception as exc:  # noqa: BLE001
                    row = dict(target, status="error",
                               error="%s: %s" % (type(exc).__name__, exc),
                               tools_found=0)
                    records = []
                with write_lock:
                    for record in records:
                        out.write(json.dumps(record, ensure_ascii=False) + "\n")
                    cov.write(json.dumps(row, ensure_ascii=False) + "\n")
                    counter["done"] += 1
                    if counter["done"] % 10 == 0:
                        cov.flush()
                        out.flush()
                        if not args.quiet:
                            elapsed = time.time() - started
                            rate = counter["done"] / elapsed if elapsed else 0
                            remaining = (len(pending) - counter["done"]) / rate if rate else 0
                            print("  %5d/%-5d  %.2f/s  eta %.0fs  %s"
                                  % (counter["done"], len(pending), rate,
                                     remaining, target["identifier"][:40]))

    print("\nwrote %s" % tools_path)
    print("wrote %s" % coverage_path)
    print("http: %s" % session.summary())


if __name__ == "__main__":
    main()
