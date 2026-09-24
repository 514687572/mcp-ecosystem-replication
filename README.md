# Replication package: the MCP server ecosystem

Code, samples, generated tables and human validation material for:

> **The Model Context Protocol Server Ecosystem: An Empirical Study of Quality,
> Security, and Evolution** — Junan Chen, University of Electronic Science and
> Technology of China.

## What is here

| Directory | Contents |
| --- | --- |
| `src/`, `scripts/` | The pipeline: harvest, analysis, enrichment, validation, packaging |
| `config/config.yaml` | Every run parameter, including the freeze date |
| `results/tables/` | The 30 result tables the manuscript reports |
| `results/validation/` | Coding worksheets, evidence packs, agreement statistics, the T1 test |
| `results/figures/` | Figures 1–4 as generated |
| `docs/` | Research plan, all three codebook versions, threats to validity, human task list |
| `paper/` | Manuscript source, fact sheet, style and compliance tooling |
| `data/interim/` | Seeded sample records and the harvest cursor |

## What is not here, and why

The raw registry harvest (`data/raw/registry.jsonl`, 131 MB and growing) is not
redistributed. The upstream registry at `registry.modelcontextprotocol.io` is
its authoritative copy, and re-publishing a snapshot invites the two copies to
diverge. `MANIFEST.csv` records the SHA-256 of the snapshot this study used, so
a fresh harvest can be checked against it.

The HTTP cache under `data/cache/` is also omitted: it is a performance
artefact, and every entry can be regenerated from the public sources.

## Reproducing the study

```
cd mcp-ecosystem-replication
python -m pip install -r requirements.txt

python scripts/01_harvest_registry.py     # data/raw/registry.jsonl
python scripts/02_analyze_registry.py     # results/tables
python scripts/03_enrich_packages.py --workers 8
python scripts/04_extract_tools.py --sample 1200 --seed 20260924
python scripts/05_enrich_github.py --releases --sample 800 --seed 20260927
python scripts/06_cross_analysis.py
python scripts/10_ingest_part_a.py --codes results/validation/T1.txt
python scripts/11_ingest_part_b.py
python scripts/12_ingest_part_c.py
python scripts/13_interrater.py
python scripts/16_version_vs_release.py
python scripts/17_build_facts.py
```

Steps 1–7 rebuild every raw input from public sources and need network access.
Steps 8–18 run offline against what those produce. Every step is resumable and
caches its HTTP responses, so an interrupted run continues where it stopped.

The `reproduce` GitHub workflow runs the offline steps and verifies
`MANIFEST.csv` on every push.

## Verifying the package

```
python scripts/verify_manifest.py
```

This recomputes the SHA-256 of every file listed in `MANIFEST.csv` and fails on
any mismatch. Line endings matter: `.gitattributes` normalises the repository to
LF, and the manifest was generated on a check-out in that state.

## Determinism

Both sampling steps use recorded seeds (`20260924` for tool extraction,
`20260927` for repository enrichment), and the drawn sets are stored under
`data/interim/`. Re-running with the same registry snapshot reproduces the same
samples. Re-running against a *newer* snapshot will not, which is why the freeze
date is a configuration value rather than a constant in the code.

## Licence

Code under MIT (`LICENSE`); data, tables and documents under CC-BY-4.0
(`LICENSE-DATA.md`).

## Building the manuscript PDF

`paper/latex/mcp-ecosystem.tex` compiles with Elsevier's CAS bundle
(`cas-dc.cls`, `cas-common.sty`, `cas-model2-names.bst`). Those files are the
publisher's copyrighted material and are deliberately not redistributed here;
download them from the journal's own template page and place them beside the
`.tex` before running:

```
powershell -ExecutionPolicy Bypass -File paper/build.ps1
```

The build also runs the journal-compliance audit, the citation check and the
style metrics, so a clean run confirms the manuscript still meets the
requirements the paper reports.
