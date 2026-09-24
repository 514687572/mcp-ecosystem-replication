"""Step 5 — enrich servers with GitHub repository facts.

About half of published servers declare a repository. This step resolves those
URLs to repository metadata and release history, which the evolution analysis
uses to compare *declared* release activity (registry versions) against
*actual* release activity (tagged GitHub releases).

GitHub rate limiting is the binding constraint:
  * unauthenticated: 60 core requests/hour, 10 search requests/minute
  * with GITHUB_TOKEN: 5,000 core requests/hour

Set GITHUB_TOKEN before running at any real scale. The job is resumable and
stops cleanly when the quota runs out.

  python scripts/05_enrich_github.py --limit 100
  python scripts/05_enrich_github.py --releases          # also fetch releases
"""
import argparse
import concurrent.futures
import json
import os
import random
import sys
import time
import threading

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from mcpstudy import config, github, registry  # noqa: E402
from mcpstudy.http import CachedSession  # noqa: E402


def load_done(path, key_field="repo_full_name"):
    done = set()
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    done.add(json.loads(line).get(key_field))
                except ValueError:
                    continue
    return done


def collect_repos(entries):
    """Distinct (owner, repo) pairs declared by latest-version servers."""
    repos = {}
    for row in registry.flatten(entries):
        owner, name = github.parse_repo_url(row.get("repository_url"))
        if not owner or not name:
            continue
        key = "%s/%s" % (owner, name)
        if key in repos:
            continue
        repos[key] = {
            "repo_full_name": key,
            "repo_owner": owner,
            "repo_name": name,
            "declared_by_server": row.get("name"),
            "declared_repository_url": row.get("repository_url"),
        }
    return list(repos.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sample", type=int, default=None,
                        help="randomly sample this many repositories instead of "
                             "taking the alphabetically first ones")
    parser.add_argument("--seed", type=int, default=20260927)
    parser.add_argument("--releases", action="store_true",
                        help="also fetch release history (costs 1-2 extra calls/repo)")
    parser.add_argument("--release-pages", type=int, default=1,
                        help="GitHub release pages to fetch per repository")
    parser.add_argument("--workers", type=int, default=4,
                        help="parallel workers; the per-host interval is per worker")
    parser.add_argument("--proxy", choices=["auto", "none"], default=None,
                        help="override the configured proxy policy; use 'none' "
                             "when a local proxy is configured but not running")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    cfg = config.load()
    if args.proxy:
        cfg["http"]["proxy_mode"] = args.proxy
    session = CachedSession(cfg)

    state = github.quota(session, cfg)
    if state:
        print("github quota: authenticated=%s core=%s/%s search=%s/%s"
              % (state["authenticated"], state["core_remaining"], state["core_limit"],
                 state["search_remaining"], state["search_limit"]))
        if not state["authenticated"]:
            print("  warning: no GITHUB_TOKEN set — expect heavy rate limiting")

    entries = registry.load_entries()
    repos = collect_repos(entries)
    repos.sort(key=lambda r: r["repo_full_name"])
    population = len(repos)
    print("distinct declared repositories: %d" % population)

    meta_path = config.out("github_repos.jsonl")
    releases_path = config.out("github_releases.jsonl")
    done = load_done(meta_path)
    pending = [r for r in repos if r["repo_full_name"] not in done]
    if args.sample and args.sample < len(pending):
        # A random draw, not the alphabetically first N: repository owners are
        # not distributed evenly across the alphabet, and the validity check
        # must not inherit that bias.
        rng = random.Random(args.seed)
        pending = sorted(rng.sample(pending, args.sample),
                         key=lambda r: r["repo_full_name"])
        print("sampled %d of %d not-yet-fetched repositories (seed %d)"
              % (len(pending), population - len(done), args.seed))
    if args.limit:
        pending = pending[: args.limit]
    print("already done: %d   pending this run: %d" % (len(done), len(pending)))
    if not pending:
        print("nothing to do")
        return

    started = time.time()
    workers = max(1, args.workers)
    worker_sessions = [CachedSession(cfg) for _ in range(workers)]
    write_lock = threading.Lock()
    counter = {"done": 0, "quota": False}

    def fetch(item, worker_session):
        """One repository, plus its releases when requested."""
        meta_row = None
        release_rows = []
        try:
            repo = github.get_repo(worker_session, cfg, item["repo_owner"],
                                   item["repo_name"])
        except github.QuotaExhausted:
            counter["quota"] = True
            return None, []
        except Exception as exc:  # noqa: BLE001
            return dict(item, status="error",
                        error="%s: %s" % (type(exc).__name__, exc)), []

        if repo is None:
            return dict(item, status="not_found"), []

        meta_row = github.repo_summary(repo)
        meta_row.update({"declared_by_server": item["declared_by_server"],
                         "status": "ok"})
        if args.releases:
            try:
                release_rows = github.get_releases(
                    worker_session, cfg, item["repo_owner"], item["repo_name"],
                    max_pages=args.release_pages)
            except Exception:  # noqa: BLE001
                release_rows = []
        return meta_row, release_rows

    stopped_early = False
    with open(meta_path, "a", encoding="utf-8") as meta_out, \
            open(releases_path, "a", encoding="utf-8") as rel_out:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {}
            for index, item in enumerate(pending):
                futures[pool.submit(fetch, item,
                                    worker_sessions[index % workers])] = item
            for future in concurrent.futures.as_completed(futures):
                item = futures[future]
                try:
                    meta_row, release_rows = future.result()
                except Exception as exc:  # noqa: BLE001
                    meta_row = dict(item, status="error",
                                    error="%s: %s" % (type(exc).__name__, exc))
                    release_rows = []
                with write_lock:
                    if meta_row is not None:
                        meta_out.write(json.dumps(meta_row, ensure_ascii=False) + "\n")
                    for row in release_rows:
                        rel_out.write(json.dumps(row, ensure_ascii=False) + "\n")
                    counter["done"] += 1
                    if counter["done"] % 20 == 0:
                        meta_out.flush()
                        rel_out.flush()
                        if not args.quiet:
                            elapsed = time.time() - started
                            rate = counter["done"] / elapsed if elapsed else 0
                            remaining = (len(pending) - counter["done"]) / rate if rate else 0
                            print("  %5d/%-5d  %.2f/s  eta %.0fs  %s"
                                  % (counter["done"], len(pending), rate, remaining,
                                     item["repo_full_name"][:40]))
                if counter["quota"]:
                    stopped_early = True
                    break

    if stopped_early:
        print("\nstopped early: GitHub quota exhausted. Re-run later to continue.")
    print("wrote %s" % meta_path)
    print("http: %s" % session.summary())


if __name__ == "__main__":
    main()
