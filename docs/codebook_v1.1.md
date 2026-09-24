# Codebook v1.1

Supersedes `codebook.md` (v1.0) for the Part B and Part C coding passes.
v1.0 is kept unchanged for provenance; the manuscript reports which version
produced which numbers.

## Why v1.1 exists

The first inter-rater round returned near-zero kappa on every field
(`results/validation/interrater_agreement.csv`). Two separate causes were
diagnosed, and both are process defects rather than coder error:

**Cause 1 — the handoff was incomplete.** The subset file given to the second
coder carried only an item id and a target name, with no manifest facts, no
description and no sibling list. The second coder's answers are the signature
of coding without evidence: `scope_breadth` was `unclear` for 25 of 25 items,
`secret_documented_as_secret` was `n/a` for 25 of 25, `desc_states_inputs` was
`n/a` for 25 of 25. Fix: `results/validation/interrater_pack.md` now embeds the
evidence for each item.

**Cause 2 — two codebook defects.**

1. `n/a` and `unclear` were both offered, and were read as synonyms by one coder
   and as opposites by the other. Collapsing them post hoc raised observed
   agreement on `secret_documented_as_secret` from 0.00 to 0.56, which confirms
   the categories were the problem.
2. `readme_warns_about_risk` had no rule for what to record when no README is
   reachable. One coder defaulted to `unclear`, the other to `no`, giving 0.00
   observed agreement on all 25 items.

A third defect was found in the primary pass: `scope_breadth` had no
`read_only` value, although 62 of 150 servers in the sample are pure readers.
The primary coder added it; the second never had it. It is now a first-class
value.

## The changes

### 1. `n/a` is almost gone

`n/a` now applies only where a field is structurally impossible:

| field | `n/a` means |
| --- | --- |
| `desc_states_inputs` | the tool takes no inputs |
| `desc_names_side_effects` | the tool is read-only by construction |
| everything else | `n/a` is not permitted |

Everywhere else, use **`undetermined`**. It is a single word for "the evidence
does not settle this", and it replaces both `unclear` and `n/a`.

### 2. Missing evidence is never coded as `no`

A field is `no` only when the evidence positively shows absence — a README that
documents risk and does not mention it, code that only reads, a manifest that
declares a required token without the secret flag. If nothing is reachable, the
code is `undetermined`. This single rule removes the `readme_warns_about_risk`
failure.

### 3. `scope_breadth` gains `read_only` and explicit thresholds

| value | threshold |
| --- | --- |
| `read_only` | every tool only reads; nothing can be changed, sent or spent |
| `narrow` | writes only to the user's own workspace or a single named item |
| `moderate` | writes to one third-party system the user explicitly connected |
| `broad` | can act on many third-party systems, or on other people |
| `undetermined` | the evidence does not say |

Apply the thresholds in order and stop at the first match. Do not reason about
how a capability *could* be used; code what the tools can do.

### 4. `desc_states_when_to_use` is tightened

`yes` requires a condition, a trigger, or an ordering rule that tells the agent
when to pick this tool over its siblings. "Use this to fetch a URL" is `no`:
it describes the purpose, not the selection condition. This field is the
study's headline claim about interface quality, so the bar has to be explicit.

### 5. Calibration before independent coding

Both coders now code five shared items together and compare, then discuss any
field they disagree on, then code the remaining items independently. Round 1
skipped this step, which is the normal reason a first kappa comes out at zero.

## What round 1 numbers may still be used for

The primary coder's 150-server and 200-tool distributions
(`part_b_summary.csv`, `part_c_summary.csv`) are the study's reported results.
The round 1 agreement statistics
(`interrater_agreement.csv`, `interrater_disagreements.csv`) may **not** be
reported as a reliability claim. They are reported, if at all, as a
methodological finding about codebook portability, with both causes above
stated.

After round 2, replace the reliability numbers and state the codebook version
that produced them.

## Versioning

Every coded row carries `codebook_version`. A row coded under v1.0 may not be
pooled with v1.1 rows in the same table without saying so.

## Round 2 outcome and what v1.2 still needs

Round 2 was run with the pack built by `scripts/14_make_interrater_pack.py`.
Reliability is reported in `results/validation/interrater_summary.csv`. Two
issues survive, and neither is a coder problem.

**1. `desc_names_side_effects` — an enumeration defect of my own making.**
v1.0 offered only `yes` / `no`; v1.1 added `n/a` for "read-only by
construction". The primary coder therefore recorded `no` where the second
recorded `n/a` for the same tools, and the field scores kappa 0.149. v1.2 must
either drop `n/a` from this field or state that `no` covers the read-only case.

**2. `desc_states_when_to_use` — a threshold, not a definition.**
kappa 0.233 with a systematic direction: the primary marked 6 of 25 items
`yes`, the second 1 of 25. The primary treats a described purpose as implying a
selection condition; the second requires an explicit condition, trigger or
ordering rule. v1.1 already tightened this rule, so tightening it again is not
obviously right — the two readings may simply both be defensible, which is why
the paper should report the range rather than a point estimate.

## Reporting rule

No field with a kappa below 0.40 may be reported as a point estimate.
Report the range across coders and say that the spread is a result.
