# Validation directory

Everything the paper needs to defend its tool-level and security-level claims.

## Coding results returned by the coder

| File | Content | Status |
| --- | --- | --- |
| `T1.txt` | Part A, 150 packages | ingested |
| `T2.txt` | Part B, 150 servers | ingested |
| `t3.txt` | Part C, 200 tools (arrives inside a ```csv fence) | ingested |
| `第二编码者编码结果.csv` | second coder, round 1, 50 items | analysed, diagnosis below |
| `第二编码者编码结果_v1.1.csv` | second coder, round 2, after calibration | analysed, results below |

## What the coders worked from

| File | Content |
| --- | --- |
| `coding_worksheet.csv` | Part A sheet, 150 rows, four columns left blank |
| `part_b_security_worksheet.csv` | Part B sheet, 150 rows |
| `part_c_tool_worksheet.csv` | Part C sheet, 200 rows |
| `extraction_evidence.txt` | Part A evidence: extracted tools plus matching source lines |
| `part_b_evidence.txt` | Part B evidence: manifest facts and links per server |
| `part_c_evidence.txt` | Part C evidence: verbatim descriptions and sibling lists |
| `extractor_agreement.csv` | per-package regex-vs-AST comparison |
| `interrater_subset.csv` | the 50 shared items (round 1 handoff — no evidence, see below) |

## Analysis outputs

| File | Answers |
| --- | --- |
| `part_a_summary.csv` | RQ4: extraction recall and precision |
| `part_a_merged.csv` | per-package human vs automated, with the reason for each miss |
| `part_a_miss_reasons.csv` | taxonomy of why the extractor missed |
| `part_b_summary.csv` | RQ2 headline metrics |
| `part_b_crosstabs.csv` | RQ2 per-field distributions |
| `part_b_by_transport.csv` | RQ2 split by hosted vs package-based |
| `part_c_summary.csv` | RQ1 description-quality metrics |
| `part_c_by_language.csv` | RQ1 split by language |
| `part_c_ambiguity.csv` | the tools an agent could confuse with a sibling |
| `interrater_agreement.csv` | round 1 kappa per field |
| `interrater_disagreements.csv` | round 2, every disagreeing cell |
| `interrater_diagnostic.csv` | round 2 kappa after collapsing unclear / n/a |
| `interrater_agreement_round1.csv` | round 1 raw kappa (not usable, see below) |
| `interrater_disagreements_round1.csv` | round 1 disagreements |
| `interrater_diagnostic_round1.csv` | round 1 collapse diagnostic |
| `interrater_agreement_harmonised.csv` | **round 2, v1.0/v1.1 wording normalised — the headline numbers** |
| `interrater_summary.csv` | round 2 harmonised, with Landis & Koch band and claim guidance |

## Round 1 inter-rater result and its cause

Round 1 produced near-zero kappa on every field. This is **not** a reliability
result and must not be reported as one. Two causes were identified:

1. **The handoff was incomplete.** `interrater_subset.csv` carried only an item
   id and a target name, with no evidence. The second coder's answers show this
   directly: `scope_breadth` was `unclear` for 25 of 25 items,
   `secret_documented_as_secret` and `desc_states_inputs` were `n/a` for 25 of
   25. They had nothing to judge from.
2. **Two codebook defects.** `n/a` and `unclear` were read as synonyms by one
   coder and as opposites by the other; and `readme_warns_about_risk` had no
   rule for the case where no README is reachable, so the two coders defaulted
   in opposite directions.

Collapsing `unclear` and `n/a` post hoc lifted observed agreement on
`secret_documented_as_secret` from 0.00 to 0.56, which is consistent with cause
2 being real rather than assumed.

## Round 2

`interrater_pack.md` is a self-contained pack: for each of the 50 items it
reproduces the manifest facts, the declared environment variables with their
secret flags, the verbatim tool description, and the sibling tool list, plus
the v1.1 rules. `interrater_worksheet.csv` is the matching blank sheet.

Round 2 was run with that pack. Results are in `interrater_summary.csv`.

### Read the harmonised file, not the raw one

The primary coder worked under codebook v1.0 and the second under v1.1. The two
versions differ in the word used for "the evidence does not settle this"
(`unclear` vs `undetermined`), so the raw comparison scores identical
judgements as disagreements. `readme_warns_about_risk` is the extreme case:
raw observed agreement 0.00, all 25 items, purely because the two coders used
different words for the same assessment.

`interrater_agreement_harmonised.csv` normalises that one wording change and
keeps every substantive code distinct. It is the file to quote.

### Round 2 reliability

| Part | Field | Observed | Kappa | Band | May carry a claim? |
| --- | --- | --- | --- | --- | --- |
| B | write_capability | 0.92 | **0.864** | almost perfect | yes |
| C | desc_states_purpose | 0.96 | **0.648** | substantial | yes |
| C | desc_states_inputs | 0.80 | **0.595** | moderate | yes, state the band |
| B | destructive_capability | 0.80 | **0.589** | moderate | yes, state the band |
| B | auth_mechanism | 0.76 | **0.525** | moderate | yes, state the band |
| B | scope_breadth | 0.64 | **0.480** | moderate | yes, state the band |
| B | requires_user_secret | 0.72 | **0.409** | moderate | borderline |
| C | desc_states_when_to_use | 0.80 | **0.233** | fair | **not as a point estimate** |
| B | secret_documented_as_secret | 0.64 | **0.229** | fair | indicative only |
| C | desc_names_side_effects | 0.24 | **0.149** | slight | no; codebook gap |
| B | readme_warns_about_risk | 1.00 | not estimable | — | no; both coders could not determine it |

### The one result that changes a paper claim

`desc_states_when_to_use` was the headline RQ1 finding ("only 23% of
descriptions say when to use the tool"). It reaches only fair agreement, and
the disagreement is systematic rather than random:

| Coder | Items marked `yes` (of 25) | Implied rate |
| --- | --- | --- |
| primary | 6 | 24% |
| second | 1 | 4% |

The primary reads a described purpose as implying a selection condition; the
second requires an explicit condition, trigger or ordering rule. On the full
200-item sample the primary's rate is 23.0%, and the automated regex heuristic
put it at 6.2%, which is close to the second coder's strict reading.

**Do not report 23% as a point estimate.** Report the range the two thresholds
bracket — roughly 4% to 24% — and say that the disagreement is itself a
finding: what counts as a selection condition is not settled even among trained
readers, which is exactly the ambiguity the study argues harms tool selection.

### Remaining codebook defect

`desc_names_side_effects` scores 0.149 because v1.0 offered only `yes`/`no`
while v1.1 added `n/a` for "read-only by construction". The primary recorded
`no` where the second recorded `n/a` for the same tools. The field cannot be
reported from this round; it needs either a v1.2 rule or a third pass.

## Round 3 (codebook v1.2)

Round 2 left four fields unusable, each for a different reason. v1.2 responds to
each and both coders re-code the same 50 items.

| Field | Round-2 kappa | Cause | v1.2 response |
| --- | --- | --- | --- |
| `desc_names_side_effects` | 0.149 | v1.0 had `yes`/`no`, v1.1 added `n/a`, so the two coders used different words for read-only tools | `n/a` removed; the field now measures disclosure only |
| `desc_states_when_to_use` | 0.233 | threshold difference, not a definition problem | binary kept, five adjudicated worked examples added |
| `secret_documented_as_secret` | 0.229 | one coder inferred from prose, the other refused to | restricted to the manifest table; prose is not evidence |
| `readme_warns_about_risk` | not estimable | neither coder could determine it for any item | **field withdrawn** |

Two files carry round 3:

| File | Purpose |
| --- | --- |
| `interrater_pack_v1.2.md` | self-contained pack: per item manifest facts, the declared-variable table with the v1.2 verdict shown, verbatim description, sibling list, and the changed rules |
| `interrater_worksheet_v1.2.csv` | matching blank sheet, 50 items, 12 fields |

Give both to each coder. When the files come back:

```powershell
python scripts\13_interrater.py --second results\validation\<returned file>.csv
```

`readme_warns_about_risk` no longer appears in the worksheet, so round 3 output
drops that row automatically.

## Networking note

The GitHub steps need outbound access to `api.github.com`. On the machine this
was built on, GitHub is only reachable through a local proxy, and that proxy
also intercepts the other hosts. When it is not running, every request fails
with `ProxyError`. Set `http.proxy_mode` in `config/config.yaml`, or pass
`--proxy none` to `scripts/05_enrich_github.py`, to bypass it.
