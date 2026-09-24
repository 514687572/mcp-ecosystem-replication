"""Step 1 — harvest every published server version from the official MCP registry.

Output: data/raw/registry.jsonl  (one JSON object per published version)
        data/interim/registry_cursor.json  (resume state)

Safe to re-run: it resumes from the stored cursor instead of starting over.
Use --fresh to discard progress and start from scratch.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from mcpstudy import config, registry  # noqa: E402
from mcpstudy.http import CachedSession  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fresh", action="store_true",
                        help="ignore saved progress and start a new harvest")
    parser.add_argument("--max-pages", type=int, default=None,
                        help="stop after this many pages (useful for a smoke test)")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if args.fresh:
        for path in (
            os.path.join(config.RAW_DIR, "registry.jsonl"),
            os.path.join(config.INTERIM_DIR, "registry_cursor.json"),
        ):
            if os.path.isfile(path):
                os.remove(path)
        print("cleared previous harvest state")

    cfg = config.load()
    session = CachedSession(cfg)
    result = registry.harvest(
        cfg=cfg,
        session=session,
        limit_pages=args.max_pages,
        verbose=not args.quiet,
    )
    print()
    for key in ("pages", "entries", "complete", "elapsed_seconds"):
        print("  %-16s %s" % (key, result[key]))
    print("  %-16s %s" % ("raw output", result["raw_path"]))
    if not result["complete"]:
        print("\n  harvest is partial — re-run this script to continue")


if __name__ == "__main__":
    main()
