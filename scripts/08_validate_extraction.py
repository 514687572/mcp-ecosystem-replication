"""Step 8 — build the tool-extraction validation pack.

The paper cannot claim a tool-level result without stating how well the
extractor recovers tools. This script produces everything needed for that
claim:

  1. a reproducible validation sample drawn with a fixed seed,
  2. an independent second opinion for Python (the AST parser, which is exact),
  3. a per-package agreement table, so disagreements can be triaged instead of
     re-read from scratch,
  4. a human coding worksheet with the codebook columns left blank,
  5. an evidence pack: for every sampled package, the extracted tools next to
     the source lines that matched, so a reviewer can confirm or refute a row in
     seconds rather than opening the archive.

Run:
  python scripts/08_validate_extraction.py --sample 150 --seed 20260925
  python scripts/08_validate_extraction.py --selftest
"""
import argparse
import csv
import json
import os
import random
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from mcpstudy import config, packages, registry, tools_extract  # noqa: E402
from mcpstudy.http import CachedSession  # noqa: E402

VALIDATION_DIR = "validation"

WORKSHEET_COLUMNS = [
    "pkg_key",
    "server_name",
    "registry_type",
    "identifier",
    "language_guess",
    "has_server_entrypoint",
    "n_tools_actual",
    "n_tools_extracted",
    "miss_reason",
    "notes",
]


def selftest():
    """Check the two extractors against a known snippet."""
    code = "\n".join([
        "import mcp",
        "",
        "@mcp.tool()",
        "async def fetch_url(url: str) -> str:",
        '    """Fetch a URL and return Markdown."""',
        "    return url",
        "",
        '@mcp.tool(name="count", description="Count tokens in text")',
        "def counter(text):",
        "    pass",
        "",
        "def build():",
        '    return Tool(name="generic", description="A generic tool",',
        "                input_schema={})",
        "",
    ])
    ast_records, ok = tools_extract.extract_python_ast(code)
    regex_records = tools_extract.extract_from_text(code, "python")
    print("AST parsed ok      :", ok)
    print("AST tools          :", [r["tool_name"] for r in ast_records])
    print("regex tools        :", [r["tool_name"] for r in regex_records])
    print("AST descriptions   :",
          [r["tool_description"][:40] for r in ast_records])
    missing = {r["tool_name"] for r in ast_records} - {
        r["tool_name"] for r in regex_records
    }
    print("AST-only (regex misses):", sorted(missing))
    return not missing


def load_coverage(path):
    rows = {}
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    row = json.loads(line)
                    rows[row["key"]] = row
    return rows


def source_snippets(root, tool_names, limit=6):
    """Collect short source excerpts around each extracted tool name."""
    snippets = []
    for path, language in tools_extract.iter_source_files(root):
        try:
            with open(path, encoding="utf-8", errors="ignore") as fh:
                lines = fh.readlines()
        except OSError:
            continue
        for index, line in enumerate(lines):
            for name in tool_names:
                if name and name in line:
                    start = max(0, index - 1)
                    end = min(len(lines), index + 4)
                    snippet = "".join(lines[start:end]).strip()
                    snippets.append(
                        "%s:%d  %s" % (os.path.relpath(path, root),
                                       index + 1, snippet[:300])
                    )
                    break
            if len(snippets) >= limit:
                return snippets
    return snippets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=int, default=150)
    parser.add_argument("--seed", type=int, default=20260925)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--keep-sources", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        ok = selftest()
        print("\nself-test:", "PASS" if ok else "FAIL")
        sys.exit(0 if ok else 1)

    cfg = config.load()
    session = CachedSession(cfg)
    out_dir = os.path.join(config.RESULTS_DIR, VALIDATION_DIR)
    os.makedirs(out_dir, exist_ok=True)

    entries = registry.load_entries()
    coverage = load_coverage(config.out("tool_extraction_coverage.jsonl"))
    extracted = {}
    tools_path = config.out("tools.jsonl")
    if os.path.isfile(tools_path):
        with open(tools_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                extracted.setdefault(row["package_key"], []).append(row)

    # Population to sample from: packages the extractor already attempted, so
    # the validation measures the extractor rather than download luck.
    population = sorted(coverage.keys())
    if not population:
        print("no coverage data yet — run scripts/04_extract_tools.py first")
        sys.exit(1)
    sample_size = min(args.sample, len(population))
    rng = random.Random(args.seed)
    sample = sorted(rng.sample(population, sample_size))
    print("validation sample: %d of %d attempted packages (seed %d)"
          % (sample_size, len(population), args.seed))

    work_root = os.path.join(config.DATA_DIR, "validation_sources")
    os.makedirs(work_root, exist_ok=True)

    worksheet_rows = []
    agreement_rows = []
    evidence_path = os.path.join(out_dir, "extraction_evidence.txt")

    with open(evidence_path, "w", encoding="utf-8") as evidence:
        for index, key in enumerate(sample, 1):
            cov = coverage[key]
            registry_type, identifier = key.split(":", 1)
            tools = extracted.get(key, [])
            names = [t["tool_name"] for t in tools]

            # Independent second opinion for Python.
            ast_names = []
            ast_ok = None
            root = None
            dest = None
            try:
                dest = os.path.join(work_root, key.replace(":", "__").replace("/", "_"))
                if registry_type == "npm":
                    meta = packages.npm_metadata(session, identifier)
                    root = packages.download_npm_tarball(
                        session, meta.get("npm_tarball"), dest
                    )
                else:
                    url = "%s/%s/json" % (cfg["packages"]["pypi_json"],
                                          packages._safe(identifier))
                    payload = session.get_json(url)
                    version = (payload.get("info") or {}).get("version")
                    root = packages.download_pypi_sdist(
                        session, identifier, version, dest
                    )
                if root:
                    for path, language in tools_extract.iter_source_files(root):
                        if language != "python":
                            continue
                        with open(path, encoding="utf-8", errors="ignore") as fh:
                            text = fh.read()
                        recs, parsed = tools_extract.extract_python_ast(text)
                        if parsed:
                            ast_ok = True
                        ast_names.extend(r["tool_name"] for r in recs)
            except Exception as exc:  # noqa: BLE001
                evidence.write("!! %s download/parse failed: %s\n" % (key, exc))

            regex_set = set(names)
            ast_set = set(ast_names)
            # The AST comparison is only meaningful where Python source was
            # actually parsed. For JavaScript packages there is no second
            # opinion, so the difference columns stay empty rather than
            # reporting every tool as a regex-only artefact.
            comparable = bool(ast_ok)
            only_regex = sorted(regex_set - ast_set) if comparable else []
            only_ast = sorted(ast_set - regex_set) if comparable else []

            agreement_rows.append(
                {
                    "pkg_key": key,
                    "registry_type": registry_type,
                    "python_parsed": bool(ast_ok),
                    "comparable": comparable,
                    "tools_regex": len(regex_set),
                    "tools_ast": len(ast_set) if comparable else "",
                    "only_in_regex": len(only_regex),
                    "only_in_ast": len(only_ast),
                    "only_in_regex_names": "|".join(only_regex[:12]),
                    "only_in_ast_names": "|".join(only_ast[:12]),
                }
            )

            worksheet_rows.append(
                {
                    "pkg_key": key,
                    "server_name": cov.get("server_name"),
                    "registry_type": registry_type,
                    "identifier": identifier,
                    "language_guess": "python" if ast_ok else (
                        "javascript" if registry_type == "npm" else "unknown"
                    ),
                    "has_server_entrypoint": "",
                    "n_tools_actual": "",
                    "n_tools_extracted": len(regex_set),
                    "miss_reason": "",
                    "notes": "",
                }
            )

            evidence.write("\n" + "=" * 78 + "\n")
            evidence.write("PACKAGE %s\n  server   %s\n  status   %s\n"
                           % (key, cov.get("server_name"), cov.get("status")))
            evidence.write("  extracted tools (%d): %s\n"
                           % (len(names), ", ".join(names[:25]) or "(none)"))
            evidence.write("  AST-only tools     : %s\n"
                           % (", ".join(only_ast[:15]) or "(none)"))
            evidence.write("  regex-only tools   : %s\n"
                           % (", ".join(only_regex[:15]) or "(none)"))
            if root:
                snippets = source_snippets(root, names[:8])
                if snippets:
                    evidence.write("  source excerpts:\n")
                    for snippet in snippets:
                        evidence.write("    %s\n" % snippet.replace("\n", "\n    "))
            if dest and not args.keep_sources:
                shutil.rmtree(dest, ignore_errors=True)

            if index % 10 == 0:
                print("  %d/%d" % (index, sample_size))

    worksheet_path = os.path.join(out_dir, "coding_worksheet.csv")
    with open(worksheet_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=WORKSHEET_COLUMNS)
        writer.writeheader()
        writer.writerows(worksheet_rows)

    agreement_path = os.path.join(out_dir, "extractor_agreement.csv")
    with open(agreement_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(agreement_rows[0].keys()))
        writer.writeheader()
        writer.writerows(agreement_rows)

    py = [r for r in agreement_rows if r["comparable"]]
    summary_rows = []
    if py:
        total_regex = sum(r["tools_regex"] for r in py)
        total_ast = sum(int(r["tools_ast"]) for r in py)
        only_regex = sum(r["only_in_regex"] for r in py)
        only_ast = sum(r["only_in_ast"] for r in py)
        shared = total_ast - only_ast
        summary_rows = [
            ("validation sample size", len(sample)),
            ("python packages comparable via AST", len(py)),
            ("tools found by regex extractor", total_regex),
            ("tools found by AST extractor", total_ast),
            ("tools agreed by both", shared),
            ("regex-only (candidate false positives)", only_regex),
            ("AST-only (extractor misses)", only_ast),
            ("estimated recall on comparable packages (%)",
             round(100.0 * shared / max(1, total_ast), 1)),
            ("candidate false positive rate (%)",
             round(100.0 * only_regex / max(1, total_regex), 1)),
        ]
        print("\npython packages parsed by AST : %d" % len(py))
        print("tools found by regex          : %d" % total_regex)
        print("tools found by AST            : %d" % total_ast)
        print("estimated recall              : %.1f%%"
              % (100.0 * shared / max(1, total_ast)))
        print("candidate false positive rate : %.1f%%"
              % (100.0 * only_regex / max(1, total_regex)))

    summary_path = os.path.join(out_dir, "extraction_quality_summary.csv")
    with open(summary_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["metric", "value"])
        writer.writerows(summary_rows)
    print("\nwrote results/validation/extraction_quality_summary.csv")

    print("\nwrote results/validation/coding_worksheet.csv")
    print("wrote results/validation/extractor_agreement.csv")
    print("wrote results/validation/extraction_evidence.txt")


if __name__ == "__main__":
    main()
