"""Verify every file in the replication package against MANIFEST.csv.

Ships with the package so a reader can confirm the deposit without trusting it.

Usage:
    python scripts/verify_manifest.py [--package <dir>]
"""
import argparse
import csv
import hashlib
import os
import sys


def sha256(path, chunk=1 << 20):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", default=os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))
    args = parser.parse_args()

    manifest = os.path.join(args.package, "MANIFEST.csv")
    if not os.path.isfile(manifest):
        print("no MANIFEST.csv in %s" % args.package)
        return 2

    checked = missing = mismatched = 0
    with open(manifest, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            full = os.path.join(args.package, row["path"])
            if not os.path.isfile(full):
                print("MISSING   %s" % row["path"])
                missing += 1
                continue
            if sha256(full) != row["sha256"]:
                print("MISMATCH  %s" % row["path"])
                mismatched += 1
                continue
            checked += 1

    print("\n%d files verified, %d missing, %d mismatched"
          % (checked, missing, mismatched))
    if missing or mismatched:
        print("note: line endings change hashes. The repository is normalised to")
        print("      LF by .gitattributes; check out without CRLF conversion.")
        return 1
    print("manifest verifies")
    return 0


if __name__ == "__main__":
    sys.exit(main())
