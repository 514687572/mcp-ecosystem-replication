# Codebook

Rules for the manual coding passes. Codes are applied to data that automation
cannot judge reliably. Keep this file and the coded CSVs in sync: if a rule
changes, the previously coded rows are invalid and must be re-coded or
explicitly versioned.

## Part A — Tool extraction validation (RQ1, RQ4)

Purpose: estimate the recall of `tools_extract.py`, and characterise what it
misses.

**Procedure.** Draw 150 packages from the tool-extraction sample. For each, read
the source and record:

| Field | Values | Notes |
| --- | --- | --- |
| `pkg_key` | string | as in `tool_extraction_coverage.jsonl` |
| `has_server_entrypoint` | yes / no / unclear | is this actually an MCP server, or a library/client? |
| `n_tools_actual` | integer | count of tools registered at runtime |
| `n_tools_extracted` | integer | from `tools.jsonl` |
| `miss_reason` | none / dynamic / config_driven / generated / obfuscated / not_a_server / other | why extraction missed, if it did |
| `notes` | free text | one line, concrete |

**Decision rules.** A "tool" is a callable exposed through the MCP `tools/list`
response, not an internal helper. Tools registered from a configuration file or
generated at runtime from an OpenAPI spec count as tools but must be marked
`config_driven` or `generated` for the miss reason if extraction fails.

Report recall as `sum(extracted) / sum(actual)` over packages with
`has_server_entrypoint = yes`, and report the miss-reason distribution.

## Part B — Security-relevant design choices (RQ2)

Purpose: code what the manifest cannot express.

Apply to 150 servers sampled from the latest-version population, stratified by
transport (hosted-only vs package-based).

| Field | Values | Notes |
| --- | --- | --- |
| `server_name` | string | registry name |
| `auth_mechanism` | none / api_key / oauth / bearer_token / basic / other / unclear | how a client authenticates |
| `auth_evidence` | url / readme / manifest / source / none | where you determined it |
| `requires_user_secret` | yes / no / unclear | does the user have to supply a credential? |
| `secret_documented_as_secret` | yes / no / n/a | is it marked secret in the registry manifest? |
| `scope_breadth` | narrow / moderate / broad / unclear | how much of the user's data or systems the tool can reach |
| `destructive_capability` | yes / no / unclear | can a tool delete, spend, send, or publish? |
| `write_capability` | yes / no / unclear | any state-changing tool |
| `readme_warns_about_risk` | yes / no | does the documentation mention security caveats? |

**Rules.** Judge only from public artefacts: the registry manifest, the
repository README and source, and the package metadata. Do not probe live
endpoints. When the evidence is absent, code `unclear` — do not infer.

## Part C — Tool description quality (RQ1)

Apply to 200 tool definitions drawn from the extracted tool set, stratified by
language.

| Field | Values | Notes |
| --- | --- | --- |
| `tool_name` | string | |
| `desc_states_purpose` | yes / partial / no | does it say what the tool does? |
| `desc_states_when_to_use` | yes / no | does it say when an agent should pick it? |
| `desc_states_inputs` | yes / no / n/a | does it explain the parameters? |
| `desc_names_side_effects` | yes / no / n/a | does it warn about writes or costs? |
| `ambiguous_with` | tool name or empty | another tool in the same server it is hard to distinguish from |

Inter-rater agreement: have a second coder code at least 50 of the 200 items
independently, and report Cohen's kappa per field. Report agreement before any
aggregate claim; if kappa is below 0.6, refine the rules and re-code rather than
publishing the aggregate.

## Versioning

Coding rules are versioned with the manuscript. Any change to a rule after
coding has started invalidates the earlier rows: record the rule version in a
`codebook_version` column so the two can be told apart.
