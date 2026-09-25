# Codebook v1.2

Supersedes v1.1 for the Part B and Part C coding passes. v1.1 remains on disk
for provenance.

## What round 2 showed

Round 2 (after the evidence pack was fixed) produced usable agreement on seven
of eleven fields. Four failed, and each failure has a different cause:

| Field | Kappa | Cause | v1.2 response |
| --- | --- | --- | --- |
| `desc_names_side_effects` | 0.149 | enumeration defect: v1.0 had `yes`/`no`, v1.1 added `n/a`, so the coders used different words for read-only tools | remove `n/a`; the field measures disclosure only |
| `desc_states_when_to_use` | 0.233 | threshold difference, not a definition problem | keep the binary, add worked examples adjudicated against our own disagreements |
| `secret_documented_as_secret` | 0.229 | one coder inferred from prose, the other refused to | restrict the field to the registry manifest; prose is not evidence |
| `readme_warns_about_risk` | not estimable | neither coder could determine it for any of the 25 items | **field removed** |

## Change 1 — `desc_names_side_effects` loses `n/a`

The field now measures exactly one thing: **does the description disclose an
effect?**

| value | meaning |
| --- | --- |
| `yes` | the description says the tool writes, deletes, spends, sends or publishes |
| `no` | the description carries no such warning, whether or not the tool is read-only |

Whether a tool is actually read-only is already measured by `write_capability`
and `destructive_capability` in Part B. Asking the same question twice, in two
vocabularies, is what broke this field.

## Change 2 — `desc_states_when_to_use` keeps its binary and gains examples

The two coders disagreed systematically rather than randomly: the primary
marked 6 of 25 items `yes`, the second 1 of 25. Reviewing the five disputed
items showed the primary was over-calling on two of them. The rule is therefore
unchanged in wording and now anchored by adjudicated examples.

A description counts as `yes` only if it gives one of:

1. **a trigger** — "when the user asks for X", "if Y is missing"
2. **an ordering rule** — "call this after X", "use this before generating Y"
3. **a disambiguation against a sibling** — "use this instead of `<sibling>` when Z"

The condition must be about **the agent's task or situation**. A qualifier that
describes **the object being acted on** is part of the purpose, not a selection
condition. This single test resolves the disputes:

| item | description (abridged) | verdict | why |
| --- | --- | --- | --- |
| C010 `studio_hold` | "Hold the shot… **Use after captions**, …" | **yes** | explicit ordering rule |
| C001 `discover_adjacent_trends` | "Find trends similar to one you've already found — … that keyword search would miss" | **no** | contrasts with an external tool, not a sibling; no condition on the agent's task |
| C016 `destroy_machine` | "Delete a Fly.io machine… **Use this to clean up machines that are no longer needed**" | **no** | "use this to `<purpose>`"; the qualifier describes the object's state |
| C003 `get_earnings_divergence` | "Cross-company analyst-management divergence detection…" | **no** | purpose only |
| C020 `end_session` | "Compatibility wrapper over checkpoint — end_session IS checkpoint" | **no** | explains when to use a *different* tool |

## Change 3 — `secret_documented_as_secret` reads the manifest only

| condition | value |
| --- | --- |
| the server declares no environment variables | `n/a` |
| it declares variables, none of which looks like a credential | `n/a` |
| it declares a credential-like variable and none is flagged secret | `no` |
| at least one credential-like variable is flagged secret | `yes` |

A prose description is **not** evidence for this field. If a server says
"no key required" in its description, that informs `auth_mechanism` and
`requires_user_secret`, not this field. The pack supplies the declared
variables and their flags for every item; code from that table alone.

## Change 4 — `readme_warns_about_risk` is withdrawn

Both coders returned "cannot determine" for all 25 items, in different words.
The evidence pack does not contain READMEs, and 23% of servers link no
repository at all, so the field cannot be answered from the artefacts we
collect. It is removed rather than redefined: a field nobody can fill produces a
number that means nothing.

Risk disclosure is still covered, by `write_capability` (kappa 0.864) and
`destructive_capability` (kappa 0.589).

## Fields to code in round 3

| Part | Fields |
| --- | --- |
| B | `auth_mechanism`, `auth_evidence`, `requires_user_secret`, `secret_documented_as_secret`, `scope_breadth`, `destructive_capability`, `write_capability` |
| C | `desc_states_purpose`, `desc_states_when_to_use`, `desc_states_inputs`, `desc_names_side_effects`, `ambiguous_with` |

`readme_warns_about_risk` is gone. Everything else is unchanged from v1.1.

## Both coders re-code

Round 3 re-codes the same 50 items under v1.2, by both coders independently. The
primary's v1.0 codes for `desc_names_side_effects` and
`secret_documented_as_secret` were produced under a different vocabulary and
scale, so they cannot simply be kept.

`desc_states_purpose`, `desc_states_inputs` and the Part B capability fields
already reached moderate or better agreement; re-coding them costs little and
produces a single consistent round.

## Addendum — the `secret_documented_as_secret` rule is not the RQ2 rule

The rules above are frozen: round 3 was coded against them and the reported
$\kappa$ belongs to this version. Do not edit them in place. This addendum
records a difference between two things that share a name.

`secret_documented_as_secret` (Part B) classifies a declared variable as
credential-like by the **permissive substring rule** — a hint such as `pat` or
`token` matching anywhere in the name. The population measurement in RQ2 uses
the **whole-word rule** instead, because the permissive one fires inside
unrelated words (`pat` in `PATH`, `token` in a "token-bucket" description) and
over-counts by roughly a factor of fourteen.

The two are not in conflict, because they answer different questions. The Part B
field asks whether *this coded server* shows a credential that the manifest does
not flag, and the pack supplies the rule's verdict so both coders apply a lookup
rather than exercise judgement. RQ2 asks how many declarations in the whole
population are in that position, which needs a rule whose precision can be
defended on its own.

The consequence to keep in mind: the permissive rule is the more inclusive of
the two, so a server coded `yes` under Part B would also be `yes` under the
whole-word rule except where the match was a location noun or a flag. Where the
manuscript reports the population figure it quotes the whole-word rule, and
Table 4 no longer carries the Part B "secret not flagged" sub-count, so no number
in the paper is derived from the permissive rule except the documented upper
bound in \S 4.2.

**Applies to**: `scripts/15_make_interrater_pack_v12.py`,
`results/validation/interrater_pack_v1.2.md`, and the round-3 worksheets, all of
which remain as coded.
