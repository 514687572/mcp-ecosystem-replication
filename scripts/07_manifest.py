"""Produce a SHA-256 manifest of everything the study depends on and produces.

This is what makes "the snapshot can be verified" a checkable claim rather than
a promise. Re-run it after any data step; the manifest is what the replication
package ships.
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from mcpstudy import config  # noqa: E402

INCLUDE_DIRS = ["data/raw", "data/interim", "data/processed",
                "results/tables", "results/figures", "config", "docs", "src", "scripts"]
EXCLUDE_SUFFIXES = (".pyc", ".tmp")


def digest(path, chunk=1 << 20):
    sha = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            sha.update(block)
    return sha.hexdigest()


def main():
    root = config.PROJECT_ROOT
    rows = []
    for rel in INCLUDE_DIRS:
        base = os.path.join(root, rel)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in ("__pycache__", "cache")]
            for filename in filenames:
                if filename.endswith(EXCLUDE_SUFFIXES):
                    continue
                full = os.path.join(dirpath, filename)
                rows.append(
                    {
                        "path": os.path.relpath(full, root).replace("\\", "/"),
                        "bytes": os.path.getsize(full),
                        "sha256": digest(full),
                    }
                )
    rows.sort(key=lambda r: r["path"])

    out_path = os.path.join(root, "MANIFEST.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "generated_by": "scripts/07_manifest.py",
                "file_count": len(rows),
                "total_bytes": sum(r["bytes"] for r in rows),
                "files": rows,
            },
            fh,
            indent=1,
        )
    print("wrote %s" % out_path)
    print("  %d files, %.1f MB"
          % (len(rows), sum(r["bytes"] for r in rows) / 1024.0 / 1024.0))
    for row in rows:
        if row["path"] in ("data/raw/registry.jsonl",
                           "data/interim/registry_cursor.json"):
            print("  key  %-34s %s  (%d bytes)"
                  % (row["path"], row["sha256"][:16], row["bytes"]))


if __name__ == "__main__":
    main()
