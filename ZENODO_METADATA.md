# Zenodo deposit: fields to fill

Upload the contents of this directory as a new Zenodo upload, then publish and
copy the DOI back into the manuscript's Data availability statement.

| Field | Value |
| --- | --- |
| Upload type | Dataset |
| Title | Replication package: The Model Context Protocol server ecosystem — an empirical study of quality, security and evolution |
| Creators | Chen, Junan (University of Electronic Science and Technology of China, ORCID 0009-0005-7969-0343) |
| Description | Pipeline, seeded samples, 30 generated result tables, human validation material and codebooks for an empirical study of the Model Context Protocol server ecosystem, frozen 24 September 2026. See README.md. |
| Licence | Creative Commons Attribution 4.0 International (CC-BY-4.0) |
| Keywords | empirical software engineering; software ecosystem; Model Context Protocol; agent tooling; replication |
| Version | 1.0.0 |
| Language | English |
| Related identifiers | The manuscript, once published |

## Then

1. Publish, and copy the **concept DOI** — this is the one that survives future
   versions.
2. In `paper/latex/mcp-refs.bib`, replace the `note` field of the
   `replicationpackage` entry with the DOI.
3. In `paper/latex/mcp-ecosystem.tex`, the Data availability statement already
   cites that entry, so no further edit is needed there.
4. Rebuild with `powershell -ExecutionPolicy Bypass -File paper/build.ps1`.
5. Optionally enable the Zenodo–GitHub integration so future releases mint a new
   version DOI automatically.

## Before depositing

- Run `python scripts/verify_manifest.py` and confirm every file matches.
- Confirm no `.env`, no token, and no raw registry snapshot is present.
