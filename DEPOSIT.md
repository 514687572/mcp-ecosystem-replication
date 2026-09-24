# Depositing this package and obtaining a DOI

**Deposited at Science Data Bank: <https://doi.org/10.57760/sciencedb.013wx>**

This is the identifier cited in the manuscript's Data availability statement.
Science Data Bank reserves the DOI at submission and makes it resolvable on
approval; the identifier does not change if the deposit is revised.

The package is published at
<https://github.com/514687572/mcp-ecosystem-replication>. A repository URL
satisfies sharing but not citation: journals that require a data deposit want a
persistent identifier. This note records how the DOI was obtained, so the
deposit can be repeated or repeated elsewhere if the identifier ever lapses.

Zenodo is unreachable from the network this package was assembled on. The
repository used instead is recorded in the manuscript's Data availability
statement, which cites the DOI directly.

## Metadata as deposited

| Field | Value |
| --- | --- |
| Title | Replication package: The Model Context Protocol server ecosystem — an empirical study of quality, security and evolution |
| Creator | Chen, Junan — University of Electronic Science and Technology of China — ORCID 0009-0005-7969-0343 |
| Type | Dataset |
| Licence | Creative Commons Attribution 4.0 International (CC-BY-4.0) |
| Language | English |
| Version | 1.0.0 |
| Publication year | 2026 |
| Keywords | empirical software engineering; software ecosystem; Model Context Protocol; agent tooling; replication |
| Description | Pipeline, seeded samples, 31 generated result tables, human-coding material and codebooks for an empirical study of the Model Context Protocol server ecosystem, frozen 24 September 2026. Includes the collection and analysis code, the two drawn samples with their seeds, the complete human validation record, and a SHA-256 manifest covering every file. |
| Related identifier | The manuscript, once published (relation: is supplement to) |

## Repositories that work from a restricted network

Tested on 24 September 2026. Zenodo returned HTTP 403; the rest were reachable.

| Repository | Notes |
| --- | --- |
| Mendeley Data (Elsevier) | Elsevier's own repository; the JSS submission flow integrates with it directly |
| Science Data Bank (Chinese Academy of Sciences) | Issues both a DOI and a CSTR identifier |
| figshare | Free, DOI |
| OSF | Free, DOI |

## Before depositing

```
python scripts/verify_manifest.py     # expect: manifest verifies
```

No `.env`, no credential and no raw registry snapshot are present in the
package; `DATA_SCOPE.md` states what is included and what is not, and why.
