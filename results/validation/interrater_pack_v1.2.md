# Inter-rater pack, round 3 (codebook v1.2)

Same 50 items as round 2, coded again under codebook v1.2.
Four fields changed; the rest are as in round 2.

Fill `interrater_worksheet_v1.2.csv`. Work independently.


---

## What changed and why

Round 2 (after the evidence pack was fixed) produced usable agreement on seven
of eleven fields. Four failed, and each failure has a different cause:

| Field | Kappa | Cause | v1.2 response |
| --- | --- | --- | --- |
| `desc_names_side_effects` | 0.149 | enumeration defect: v1.0 had `yes`/`no`, v1.1 added `n/a`, so the coders used different words for read-only tools | remove `n/a`; the field measures disclosure only |
| `desc_states_when_to_use` | 0.233 | threshold difference, not a definition problem | keep the binary, add worked examples adjudicated against our own disagreements |
| `secret_documented_as_secret` | 0.229 | one coder inferred from prose, the other refused to | restrict the field to the registry manifest; prose is not evidence |
| `readme_warns_about_risk` | not estimable | neither coder could determine it for any of the 25 items | **field removed** |

## Change 1 — desc_names_side_effects

The field now measures exactly one thing: **does the description disclose an
effect?**

| value | meaning |
| --- | --- |
| `yes` | the description says the tool writes, deletes, spends, sends or publishes |
| `no` | the description carries no such warning, whether or not the tool is read-only |

Whether a tool is actually read-only is already measured by `write_capability`
and `destructive_capability` in Part B. Asking the same question twice, in two
vocabularies, is what broke this field.

## Change 2 — desc_states_when_to_use

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

## Change 3 — secret_documented_as_secret

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

## Change 4 — readme_warns_about_risk withdrawn

Both coders returned "cannot determine" for all 25 items, in different words.
The evidence pack does not contain READMEs, and 23% of servers link no
repository at all, so the field cannot be answered from the artefacts we
collect. It is removed rather than redefined: a field nobody can fill produces a
number that means nothing.

Risk disclosure is still covered, by `write_capability` (kappa 0.864) and
`destructive_capability` (kappa 0.589).

---

# Part B items


## B001 — ai.edgechat/edgepedia

| manifest field | value |
| --- | --- |
| title | Edgepedia |
| description | Search and read Edgepedia, a free and growing encyclopedia with citations. No key. |
| transport | streamable-http |
| packages | (none) |
| repository | (none) |
| website | https://www.edgechat.ai/developers |

**Declared environment variables (0)** — the only evidence for secret_documented_as_secret:

_none declared_

> v1.2 manifest rule gives **N/A** for this item (no environment variables declared).
> Confirm it yourself from the table above.

Codes to assign: auth_mechanism, auth_evidence, requires_user_secret, secret_documented_as_secret, scope_breadth, destructive_capability, write_capability.


## B002 — ai.getvda/structured-output-agent

| manifest field | value |
| --- | --- |
| title | (none) |
| description | Structured Output MCP Agent |
| transport | streamable-http |
| packages | (none) |
| repository | (none) |
| website | https://structured-output-agent.getvda.ai |

**Declared environment variables (0)** — the only evidence for secret_documented_as_secret:

_none declared_

> v1.2 manifest rule gives **N/A** for this item (no environment variables declared).
> Confirm it yourself from the table above.

Codes to assign: auth_mechanism, auth_evidence, requires_user_secret, secret_documented_as_secret, scope_breadth, destructive_capability, write_capability.


## B003 — ai.meetlark/mcp-server

| manifest field | value |
| --- | --- |
| title | (none) |
| description | Agent-first meeting schedule polls for humans and agents. Create polls, vote, find times. |
| transport | stdio|streamable-http |
| packages | npm |
| repository | (none) |
| website | (none) |

**Declared environment variables (0)** — the only evidence for secret_documented_as_secret:

_none declared_

> v1.2 manifest rule gives **N/A** for this item (no environment variables declared).
> Confirm it yourself from the table above.

Codes to assign: auth_mechanism, auth_evidence, requires_user_secret, secret_documented_as_secret, scope_breadth, destructive_capability, write_capability.


## B004 — ai.namewhisper/ens-tools

| manifest field | value |
| --- | --- |
| title | Name Whisper — ENS Intelligence Layer |
| description | 44 MCP tools to search, value, register, trade, and manage ENS names. AI-powered intelligence layer. |
| transport | streamable-http |
| packages | (none) |
| repository | https://github.com/eggybug42069/namewhisper-mcp |
| website | https://namewhisper.ai |

**Declared environment variables (0)** — the only evidence for secret_documented_as_secret:

_none declared_

> v1.2 manifest rule gives **N/A** for this item (no environment variables declared).
> Confirm it yourself from the table above.

Codes to assign: auth_mechanism, auth_evidence, requires_user_secret, secret_documented_as_secret, scope_breadth, destructive_capability, write_capability.


## B005 — ai.primeta/primeta

| manifest field | value |
| --- | --- |
| title | Primeta |
| description | Give your AI a face, a voice, and a personality. 3D avatars with custom personas. |
| transport | streamable-http |
| packages | (none) |
| repository | (none) |
| website | https://primeta.ai |

**Declared environment variables (0)** — the only evidence for secret_documented_as_secret:

_none declared_

> v1.2 manifest rule gives **N/A** for this item (no environment variables declared).
> Confirm it yourself from the table above.

Codes to assign: auth_mechanism, auth_evidence, requires_user_secret, secret_documented_as_secret, scope_breadth, destructive_capability, write_capability.


## B006 — ai.smithery/mrugankpednekar-bill_splitter_mcp

| manifest field | value |
| --- | --- |
| title | (none) |
| description | Track and split shared expenses across trips, events, and groups. Create groups, add expenses, and… |
| transport | streamable-http |
| packages | (none) |
| repository | https://github.com/mrugankpednekar/bill_splitter_mcp |
| website | (none) |

**Declared environment variables (0)** — the only evidence for secret_documented_as_secret:

_none declared_

> v1.2 manifest rule gives **N/A** for this item (no environment variables declared).
> Confirm it yourself from the table above.

Codes to assign: auth_mechanism, auth_evidence, requires_user_secret, secret_documented_as_secret, scope_breadth, destructive_capability, write_capability.


## B007 — ai.smithery/zwldarren-akshare-one-mcp

| manifest field | value |
| --- | --- |
| title | (none) |
| description | Provide access to Chinese stock market data including historical prices, real-time data, news, and… |
| transport | streamable-http |
| packages | (none) |
| repository | https://github.com/zwldarren/akshare-one-mcp |
| website | (none) |

**Declared environment variables (0)** — the only evidence for secret_documented_as_secret:

_none declared_

> v1.2 manifest rule gives **N/A** for this item (no environment variables declared).
> Confirm it yourself from the table above.

Codes to assign: auth_mechanism, auth_evidence, requires_user_secret, secret_documented_as_secret, scope_breadth, destructive_capability, write_capability.


## B008 — ai.strix/strix

| manifest field | value |
| --- | --- |
| title | Strix |
| description | AI pentesting: run scans, triage vulnerabilities, review PRs, manage schedules and assets. |
| transport | streamable-http |
| packages | (none) |
| repository | (none) |
| website | https://strix.ai |

**Declared environment variables (0)** — the only evidence for secret_documented_as_secret:

_none declared_

> v1.2 manifest rule gives **N/A** for this item (no environment variables declared).
> Confirm it yourself from the table above.

Codes to assign: auth_mechanism, auth_evidence, requires_user_secret, secret_documented_as_secret, scope_breadth, destructive_capability, write_capability.


## B009 — ai.zencap/zencap

| manifest field | value |
| --- | --- |
| title | (none) |
| description | Institutional financial data with SEC filing citations, for every AI agent. OAuth 2.1. |
| transport | streamable-http |
| packages | (none) |
| repository | (none) |
| website | https://zencap.ai |

**Declared environment variables (0)** — the only evidence for secret_documented_as_secret:

_none declared_

> v1.2 manifest rule gives **N/A** for this item (no environment variables declared).
> Confirm it yourself from the table above.

Codes to assign: auth_mechanism, auth_evidence, requires_user_secret, secret_documented_as_secret, scope_breadth, destructive_capability, write_capability.


## B010 — app.cannonstudio/cannon-studio

| manifest field | value |
| --- | --- |
| title | Cannon Studio |
| description | Public Cannon Studio MCP for product, pricing, workflow, model, and API answers. |
| transport | streamable-http |
| packages | (none) |
| repository | (none) |
| website | (none) |

**Declared environment variables (0)** — the only evidence for secret_documented_as_secret:

_none declared_

> v1.2 manifest rule gives **N/A** for this item (no environment variables declared).
> Confirm it yourself from the table above.

Codes to assign: auth_mechanism, auth_evidence, requires_user_secret, secret_documented_as_secret, scope_breadth, destructive_capability, write_capability.


## B011 — app.wishpool/ireland-payments-mcp

| manifest field | value |
| --- | --- |
| title | Ireland Payments (Stripe — cards / Apple Pay) |
| description | Ireland payments for AI agents — cards / Apple Pay via Stripe. Never holds funds. |
| transport | streamable-http |
| packages | (none) |
| repository | https://github.com/junter1989k-ai/ireland-payments-mcp |
| website | https://github.com/junter1989k-ai/ireland-payments-mcp |

**Declared environment variables (0)** — the only evidence for secret_documented_as_secret:

_none declared_

> v1.2 manifest rule gives **N/A** for this item (no environment variables declared).
> Confirm it yourself from the table above.

Codes to assign: auth_mechanism, auth_evidence, requires_user_secret, secret_documented_as_secret, scope_breadth, destructive_capability, write_capability.


## B012 — cat.churchofai/aigora

| manifest field | value |
| --- | --- |
| title | Church of AI & Cats |
| description | A half-joking Polish church for AI agents: doctrine, confessional with penance, agent forum. |
| transport | streamable-http |
| packages | (none) |
| repository | https://github.com/Wrk2525/Aigora |
| website | https://churchofai.cat/skill.md |

**Declared environment variables (0)** — the only evidence for secret_documented_as_secret:

_none declared_

> v1.2 manifest rule gives **N/A** for this item (no environment variables declared).
> Confirm it yourself from the table above.

Codes to assign: auth_mechanism, auth_evidence, requires_user_secret, secret_documented_as_secret, scope_breadth, destructive_capability, write_capability.


## B013 — ch.martinelli/jooq-mcp

| manifest field | value |
| --- | --- |
| title | (none) |
| description | An MCP server that provides access to the jOOQ documentation |
| transport | sse |
| packages | (none) |
| repository | https://github.com/martinellich/jooq-mcp |
| website | (none) |

**Declared environment variables (0)** — the only evidence for secret_documented_as_secret:

_none declared_

> v1.2 manifest rule gives **N/A** for this item (no environment variables declared).
> Confirm it yourself from the table above.

Codes to assign: auth_mechanism, auth_evidence, requires_user_secret, secret_documented_as_secret, scope_breadth, destructive_capability, write_capability.


## B014 — club.atlasyield/mcp

| manifest field | value |
| --- | --- |
| title | AtlasYield |
| description | DeFi vault judgment for agents: 16-factor Atlas Score, route survival, blowup alerts. Read-only. |
| transport | stdio |
| packages | npm |
| repository | https://github.com/gveshk/atlasyield-mcp |
| website | https://docs.atlasyield.club/api-reference/mcp |

**Declared environment variables (0)** — the only evidence for secret_documented_as_secret:

_none declared_

> v1.2 manifest rule gives **N/A** for this item (no environment variables declared).
> Confirm it yourself from the table above.

Codes to assign: auth_mechanism, auth_evidence, requires_user_secret, secret_documented_as_secret, scope_breadth, destructive_capability, write_capability.


## B015 — com.agentery/agentery

| manifest field | value |
| --- | --- |
| title | (none) |
| description | Price benchmarks, alternatives & daily price history across 17,000+ AI agents and MCP servers. |
| transport | streamable-http |
| packages | (none) |
| repository | (none) |
| website | https://agentery.com |

**Declared environment variables (0)** — the only evidence for secret_documented_as_secret:

_none declared_

> v1.2 manifest rule gives **N/A** for this item (no environment variables declared).
> Confirm it yourself from the table above.

Codes to assign: auth_mechanism, auth_evidence, requires_user_secret, secret_documented_as_secret, scope_breadth, destructive_capability, write_capability.


## B016 — com.astryke/hub

| manifest field | value |
| --- | --- |
| title | Astryke Hub |
| description | Every project you have going, on one board your coding agents keep current and you actually read. |
| transport | streamable-http |
| packages | (none) |
| repository | (none) |
| website | https://astryke.com |

**Declared environment variables (0)** — the only evidence for secret_documented_as_secret:

_none declared_

> v1.2 manifest rule gives **N/A** for this item (no environment variables declared).
> Confirm it yourself from the table above.

Codes to assign: auth_mechanism, auth_evidence, requires_user_secret, secret_documented_as_secret, scope_breadth, destructive_capability, write_capability.


## B017 — com.bynn/bynn

| manifest field | value |
| --- | --- |
| title | Bynn |
| description | Document fraud detection for manipulated, fake and AI-generated PDF and image documents. |
| transport | streamable-http |
| packages | (none) |
| repository | https://github.com/Bynn-Intelligence/skills |
| website | https://docs.bynn.com |

**Declared environment variables (0)** — the only evidence for secret_documented_as_secret:

_none declared_

> v1.2 manifest rule gives **N/A** for this item (no environment variables declared).
> Confirm it yourself from the table above.

Codes to assign: auth_mechanism, auth_evidence, requires_user_secret, secret_documented_as_secret, scope_breadth, destructive_capability, write_capability.


## B018 — com.dexpaprika/dexpaprika

| manifest field | value |
| --- | --- |
| title | DexPaprika |
| description | DEX and on-chain data: liquidity pools, token prices, swaps, and trading volume. |
| transport | sse|streamable-http |
| packages | (none) |
| repository | https://github.com/coinpaprika/dexpaprika-mcp |
| website | (none) |

**Declared environment variables (0)** — the only evidence for secret_documented_as_secret:

_none declared_

> v1.2 manifest rule gives **N/A** for this item (no environment variables declared).
> Confirm it yourself from the table above.

Codes to assign: auth_mechanism, auth_evidence, requires_user_secret, secret_documented_as_secret, scope_breadth, destructive_capability, write_capability.


## B019 — com.discoverseniorbenefits/benefits

| manifest field | value |
| --- | --- |
| title | DiscoverSeniorBenefits |
| description | Find US senior benefits by ZIP and check eligibility via deterministic rules citing .gov sources. |
| transport | streamable-http |
| packages | (none) |
| repository | (none) |
| website | https://discoverseniorbenefits.com/ai |

**Declared environment variables (0)** — the only evidence for secret_documented_as_secret:

_none declared_

> v1.2 manifest rule gives **N/A** for this item (no environment variables declared).
> Confirm it yourself from the table above.

Codes to assign: auth_mechanism, auth_evidence, requires_user_secret, secret_documented_as_secret, scope_breadth, destructive_capability, write_capability.


## B020 — com.eqiqs/eqiqs

| manifest field | value |
| --- | --- |
| title | eqiqs |
| description | 21-framework people intelligence and compatibility scoring for any MCP client. |
| transport | streamable-http |
| packages | (none) |
| repository | https://github.com/EQIQs/mcp-server |
| website | https://www.eqiqs.com/mcp |

**Declared environment variables (0)** — the only evidence for secret_documented_as_secret:

_none declared_

> v1.2 manifest rule gives **N/A** for this item (no environment variables declared).
> Confirm it yourself from the table above.

Codes to assign: auth_mechanism, auth_evidence, requires_user_secret, secret_documented_as_secret, scope_breadth, destructive_capability, write_capability.


## B021 — com.files/python-mcp

| manifest field | value |
| --- | --- |
| title | (none) |
| description | Local-only Python MCP server for the Files.com API. |
| transport | stdio |
| packages | pypi |
| repository | https://github.com/Files-com/files-mcp |
| website | (none) |

**Declared environment variables (2)** — the only evidence for secret_documented_as_secret:

| variable | required | flagged secret |
| --- | --- | --- |
| FILES_COM_API_KEY | True | True |
| FILES_COM_LOCAL_ROOT | False | False |

> v1.2 manifest rule gives **YES** for this item (at least one credential-like variable flagged secret).
> Confirm it yourself from the table above.

Codes to assign: auth_mechanism, auth_evidence, requires_user_secret, secret_documented_as_secret, scope_breadth, destructive_capability, write_capability.


## B022 — com.getlandlens/landlens

| manifest field | value |
| --- | --- |
| title | LandLens rental records |
| description | Owner of record, code violations, evictions and tenant reviews for US college-town rentals. |
| transport | streamable-http |
| packages | (none) |
| repository | (none) |
| website | https://getlandlens.com/api |

**Declared environment variables (0)** — the only evidence for secret_documented_as_secret:

_none declared_

> v1.2 manifest rule gives **N/A** for this item (no environment variables declared).
> Confirm it yourself from the table above.

Codes to assign: auth_mechanism, auth_evidence, requires_user_secret, secret_documented_as_secret, scope_breadth, destructive_capability, write_capability.


## B023 — com.immo-spot/mcp

| manifest field | value |
| --- | --- |
| title | Immo Spot MCP |
| description | Données immobilières officielles françaises (DVF+, cadastre, DPE, risques, urbanisme) via MCP. |
| transport | streamable-http |
| packages | (none) |
| repository | (none) |
| website | https://immo-spot.com/mcp-server-data-immobilier |

**Declared environment variables (0)** — the only evidence for secret_documented_as_secret:

_none declared_

> v1.2 manifest rule gives **N/A** for this item (no environment variables declared).
> Confirm it yourself from the table above.

Codes to assign: auth_mechanism, auth_evidence, requires_user_secret, secret_documented_as_secret, scope_breadth, destructive_capability, write_capability.


## B024 — com.invoicedataextraction/invoice-data-extraction

| manifest field | value |
| --- | --- |
| title | Invoice Data Extraction |
| description | Invoices and other financial documents to rows: upload, say what to extract, read the rows. |
| transport | streamable-http |
| packages | (none) |
| repository | (none) |
| website | https://invoicedataextraction.com/docs/mcp |

**Declared environment variables (0)** — the only evidence for secret_documented_as_secret:

_none declared_

> v1.2 manifest rule gives **N/A** for this item (no environment variables declared).
> Confirm it yourself from the table above.

Codes to assign: auth_mechanism, auth_evidence, requires_user_secret, secret_documented_as_secret, scope_breadth, destructive_capability, write_capability.


## B025 — com.mcparmory/polygon

| manifest field | value |
| --- | --- |
| title | (none) |
| description | Access stock, crypto, and ETF market data, analyst ratings, earnings, and financial news |
| transport | stdio |
| packages | oci|pypi |
| repository | https://github.com/mcparmory/registry |
| website | (none) |

**Declared environment variables (0)** — the only evidence for secret_documented_as_secret:

_none declared_

> v1.2 manifest rule gives **N/A** for this item (no environment variables declared).
> Confirm it yourself from the table above.

Codes to assign: auth_mechanism, auth_evidence, requires_user_secret, secret_documented_as_secret, scope_breadth, destructive_capability, write_capability.


---

# Part C items


## C001 — discover_adjacent_trends

Server: `ai.fodda/mcp-server`  Language: javascript/typescript

**Description (verbatim):**

> Find trends similar to one you've already found — surfaces unexpected cross-domain connections that keyword search would miss. Returns scored similarity matches and optionally editorial links across graphs. Use to expand research briefs, discover cross-industry parallels, or map the territory around a strong signal. This leverages Fodda's proprietary similarity index across all knowledge graphs.


**Sibling tools (50):** research_report, source_plan, research_result, raw_data, get_my_account, list_graphs, get_capabilities, list_analysts, search_graph, get_neighbors, get_evidence, get_node, get_label_values, brand_tracker, get_supplemental_context, check_supplemental_status, get_domain_intelligence, get_expert_intelligence, get_report_intelligence, search_statistics, search_insights, draft_linkedin_post, draft_linkedin_article, get_earnings_intelligence, get_earnings_divergence


Codes to assign: desc_states_purpose, desc_states_when_to_use, desc_states_inputs, desc_names_side_effects, ambiguous_with.


## C002 — expert_onboarding_research

Server: `ai.fodda/mcp-server`  Language: javascript/typescript

**Description (verbatim):**

> Kick off asynchronous background research on your public work for the expert onboarding. The identity is derived from your connector session. When beginning the analysis for stage 3 (indexing/reading back through conversations and meeting transcripts), explicitly reassure the expert:


**Sibling tools (50):** research_report, source_plan, research_result, raw_data, get_my_account, list_graphs, get_capabilities, list_analysts, search_graph, get_neighbors, get_evidence, get_node, get_label_values, discover_adjacent_trends, brand_tracker, get_supplemental_context, check_supplemental_status, get_domain_intelligence, get_expert_intelligence, get_report_intelligence, search_statistics, search_insights, draft_linkedin_post, draft_linkedin_article, get_earnings_intelligence


Codes to assign: desc_states_purpose, desc_states_when_to_use, desc_states_inputs, desc_names_side_effects, ambiguous_with.


## C003 — get_earnings_divergence

Server: `ai.fodda/mcp-server`  Language: javascript/typescript

**Description (verbatim):**

> Cross-company analyst-management divergence detection from the knowledge graph (legacy-thematic). Surfaces where executives are deflecting, reframing, or avoiding specific topics — the gap between what analysts press on and how management responds. Use for


**Sibling tools (50):** research_report, source_plan, research_result, raw_data, get_my_account, list_graphs, get_capabilities, list_analysts, search_graph, get_neighbors, get_evidence, get_node, get_label_values, discover_adjacent_trends, brand_tracker, get_supplemental_context, check_supplemental_status, get_domain_intelligence, get_expert_intelligence, get_report_intelligence, search_statistics, search_insights, draft_linkedin_post, draft_linkedin_article, get_earnings_intelligence


Codes to assign: desc_states_purpose, desc_states_when_to_use, desc_states_inputs, desc_names_side_effects, ambiguous_with.


## C004 — sign_up_free_account

Server: `ai.fodda/mcp-server`  Language: javascript/typescript

**Description (verbatim):**

> Create a free Fodda Base account (100 API calls/month across ALL knowledge graphs) and send a confirmation email. GUARDRAIL: only call this AFTER the user has explicitly provided their email and asked to create an account — never sign someone up proactively or with an email inferred from earlier context. Can also pass profile fields (name, job_title, company).


**Sibling tools (50):** research_report, source_plan, research_result, raw_data, get_my_account, list_graphs, get_capabilities, list_analysts, search_graph, get_neighbors, get_evidence, get_node, get_label_values, discover_adjacent_trends, brand_tracker, get_supplemental_context, check_supplemental_status, get_domain_intelligence, get_expert_intelligence, get_report_intelligence, search_statistics, search_insights, draft_linkedin_post, draft_linkedin_article, get_earnings_intelligence


Codes to assign: desc_states_purpose, desc_states_when_to_use, desc_states_inputs, desc_names_side_effects, ambiguous_with.


## C005 — navigator_query

Server: `ai.mentu/navigator`  Language: javascript/typescript

**Description (verbatim):**

> Specialist tool: find and rank source-backed repository evidence for a natural-language or exact query.


**Sibling tools (7):** navigator, locate, read_range, navigator_handles, navigator_map, navigator_symbol_context, navigator_change_impact


Codes to assign: desc_states_purpose, desc_states_when_to_use, desc_states_inputs, desc_names_side_effects, ambiguous_with.


## C006 — sap_give_feedback

Server: `ai.oobeprotocol.sap.mcp/sap-mcp`  Language: javascript/typescript

**Description (verbatim):**

> Create on-chain feedback for an agent wallet.


**Sibling tools (151):** oobe-sap-mcp, includeWallet, includeProfiles, userIntent, targetTool, lastError, goal, errorMessage, transactionSignature, cluster, projectType, features, executionHash, agentWallet, includeCode, proofData, expectedHash, onChain, serviceName, priceSol, endpoint, timeout, detailed, includeTransactions, agentType


Codes to assign: desc_states_purpose, desc_states_when_to_use, desc_states_inputs, desc_names_side_effects, ambiguous_with.


## C007 — sap_skills_upgrade_plan

Server: `ai.oobeprotocol.sap.mcp/sap-mcp`  Language: javascript/typescript

**Description (verbatim):**

> Free helper that returns exact latest-release commands and target directories for upgrading SAP MCP skills. Hosted mode returns a local action plan; local mode can then use sap_skills_install to write files.


**Sibling tools (151):** oobe-sap-mcp, includeWallet, includeProfiles, userIntent, targetTool, lastError, goal, errorMessage, transactionSignature, cluster, projectType, features, executionHash, agentWallet, includeCode, proofData, expectedHash, onChain, serviceName, priceSol, endpoint, timeout, detailed, includeTransactions, agentType


Codes to assign: desc_states_purpose, desc_states_when_to_use, desc_states_inputs, desc_names_side_effects, ambiguous_with.


## C008 — sap_x402_estimate_cost

Server: `ai.oobeprotocol.sap.mcp/sap-mcp`  Language: javascript/typescript

**Description (verbatim):**

> Estimate cost for a number of calls using SDK X402Registry.estimateCost. Reads escrow/pricing when available and supports optional volume curve overrides.


**Sibling tools (151):** oobe-sap-mcp, includeWallet, includeProfiles, userIntent, targetTool, lastError, goal, errorMessage, transactionSignature, cluster, projectType, features, executionHash, agentWallet, includeCode, proofData, expectedHash, onChain, serviceName, priceSol, endpoint, timeout, detailed, includeTransactions, agentType


Codes to assign: desc_states_purpose, desc_states_when_to_use, desc_states_inputs, desc_names_side_effects, ambiguous_with.


## C009 — import_resume_from_text

Server: `com.aicandidatehub/mcp`  Language: javascript/typescript

**Description (verbatim):**

> Import a resume (also called CV — terms interchangeable) from plain text. Parses the text and persists it as a new CV profile in the user's candidate-profiles library. Returns the new cv_profile_id for use with analyze_job_fit, generate_cover_letter, and rewrite_cv_for_job.


**Sibling tools (17):** analyze_compensation_for_job, analyze_job_fit, generate_cover_letter, get_compensation_for_role, get_cv_download_url, get_job, get_profile, get_server_info, get_tracked_job, import_job_from_url, list_cv_profiles, list_generated_cvs, list_jobs, list_tracked_jobs, rewrite_cv_for_job, signup_url, track_job


Codes to assign: desc_states_purpose, desc_states_when_to_use, desc_states_inputs, desc_names_side_effects, ambiguous_with.


## C010 — studio_hold

Server: `com.aioproductos/mcp-studio`  Language: javascript/typescript

**Description (verbatim):**

> Hold the shot for a moment — glides to a target (optional) and keeps micro-drift so the recorder keeps emitting frames (a dead-static hold gets its tail frames dropped). Use after captions, highlights, and zooms: 2000–3000ms is a good beat.


**Sibling tools (13):** studio_start, studio_goto, studio_click, studio_type, studio_scroll, studio_caption, studio_narrate, studio_highlight, studio_zoom, studio_end_card, studio_screenshot, studio_finish, studio_cancel


Codes to assign: desc_states_purpose, desc_states_when_to_use, desc_states_inputs, desc_names_side_effects, ambiguous_with.


## C011 — openPorts

Server: `com.geekflare/mcp`  Language: javascript/typescript

**Description (verbatim):**

> Scan open ports on a host and optionally detect running services


**Sibling tools (17):** webScrape, metaScrape, screenshot, search, dnsRecord, siteStatus, redirectCheck, brokenLink, url2Pdf, tlsScan, loadTime, mixedContent, dnsSec, mtr, ping, lighthouse, brand


Codes to assign: desc_states_purpose, desc_states_when_to_use, desc_states_inputs, desc_names_side_effects, ambiguous_with.


## C012 — ga4_get_audience_export_diagnostics

Server: `com.getmcpads/google-analytics`  Language: javascript/typescript

**Description (verbatim):**

> Read-only Audience Export diagnostics. Lists existing audience exports, state counts, and optionally samples rows from an existing export.


**Sibling tools (26):** ga4_run_pivot_report, ga4_batch_run_reports, ga4_batch_run_pivot_reports, ga4_check_compatibility, ga4_get_property_quotas_snapshot, ga4_list_accounts, ga4_list_admin_resources, ga4_get_property_configuration, ga4_list_audience_exports, ga4_query_audience_export, ga4_health_check, ga4_list_properties, ga4_run_report, ga4_run_realtime_report, ga4_get_metadata, ga4_get_custom_definitions, ga4_get_key_events, ga4_get_ecommerce_diagnostics, ga4_get_event_parameters, ga4_run_funnel_recipe, ga4_get_audience_diagnostics, ga4_get_bigquery_export_diagnostics, ga4_get_server_side_tagging_diagnostics, ga4_run_advanced_funnel_report, ga4_get_channel_groups


Codes to assign: desc_states_purpose, desc_states_when_to_use, desc_states_inputs, desc_names_side_effects, ambiguous_with.


## C013 — gsc_get_sitemap_health

Server: `com.getmcpads/google-search-console`  Language: javascript/typescript

**Description (verbatim):**

> Return an enriched read-only sitemap health summary with status totals, submitted/indexed content counts, warnings, and errors.


**Sibling tools (19):** gsc_list_sites, gsc_get_site, gsc_health_check, gsc_query_search_analytics, gsc_inspect_url, gsc_bulk_inspect_urls, gsc_list_sitemaps, gsc_get_sitemap, gsc_compare_search_types, gsc_get_data_freshness, gsc_monitor_indexation_freshness, gsc_track_sitemap_deltas, gsc_analyze_search_appearance_trends, gsc_plan_large_site_sampling, gsc_indexation_watchlist, gsc_find_losses_gains, gsc_cluster_queries, gsc_detect_cannibalization, gsc_validate_query


Codes to assign: desc_states_purpose, desc_states_when_to_use, desc_states_inputs, desc_names_side_effects, ambiguous_with.


## C014 — gsc_list_sitemaps

Server: `com.getmcpads/google-search-console`  Language: javascript/typescript

**Description (verbatim):**

> List sitemaps submitted for a Search Console property, including processing status and submitted/indexed counts.


**Sibling tools (19):** gsc_list_sites, gsc_get_site, gsc_health_check, gsc_query_search_analytics, gsc_inspect_url, gsc_bulk_inspect_urls, gsc_get_sitemap, gsc_get_sitemap_health, gsc_compare_search_types, gsc_get_data_freshness, gsc_monitor_indexation_freshness, gsc_track_sitemap_deltas, gsc_analyze_search_appearance_trends, gsc_plan_large_site_sampling, gsc_indexation_watchlist, gsc_find_losses_gains, gsc_cluster_queries, gsc_detect_cannibalization, gsc_validate_query


Codes to assign: desc_states_purpose, desc_states_when_to_use, desc_states_inputs, desc_names_side_effects, ambiguous_with.


## C015 — prophetx_list_positions

Server: `com.parlayx/mcp`  Language: javascript/typescript

**Description (verbatim):**

> List the calling actor


**Sibling tools (38):** whoami, get_time, list_sports, list_competitions, list_events, list_event_markets, lookup_market, kalshi_list_orders, kalshi_get_order, kalshi_get_order_fills, kalshi_list_positions, kalshi_get_balance, kalshi_submit_order, kalshi_cancel_order, limitless_list_markets, limitless_list_orders, limitless_get_order, limitless_get_order_fills, limitless_list_positions, limitless_get_balance, limitless_submit_order, limitless_cancel_order, limitless_replace_order, limitless_replace_orders, polymarket_list_orders


Codes to assign: desc_states_purpose, desc_states_when_to_use, desc_states_inputs, desc_names_side_effects, ambiguous_with.


## C016 — destroy_machine

Server: `com.pulsemcp/proctor`  Language: javascript/typescript

**Description (verbatim):**

> Delete a Fly.io machine. Permanently removes a Fly machine that was used for Proctor exam execution. Use this to clean up machines that are no longer needed. **Returns:** - success: boolean indicating if the machine was deleted **Use cases:** - Clean up machines after exam completion - Remove stuck or failed machines - Free up resources - Remove machines that are no longer needed **Warning:** - This action is irreversible - Any running processes on the machine will be terminated - Use cancel_exam first if there


**Sibling tools (7):** PROCTOR_API_KEY, PROCTOR_API_URL, TOOL_GROUPS, cancel_exam, get_machines, get_proctor_metadata, run_exam


Codes to assign: desc_states_purpose, desc_states_when_to_use, desc_states_inputs, desc_names_side_effects, ambiguous_with.


## C017 — list_contacts

Server: `com.rcs-campaigns/campaigns`  Language: javascript/typescript

**Description (verbatim):**

> Search the org


**Sibling tools (57):** Discovery, Templates, Surveys, Campaigns, Conversations, Contacts, Audiences, Webhooks, Media, Usage, capabilities, search_templates, get_template, render_template, create_template, update_template, duplicate_template, delete_template, clone_template, submit_template, send_message, search_surveys, get_survey, render_survey, create_survey


Codes to assign: desc_states_purpose, desc_states_when_to_use, desc_states_inputs, desc_names_side_effects, ambiguous_with.


## C018 — scrapeer_list_flows

Server: `com.scrapeer/mcp-server`  Language: javascript/typescript

**Description (verbatim):**

> List your saved scraping flows.


**Sibling tools (14):** scrapeer_get_flow, scrapeer_run_flow, scrapeer_run_flow_and_wait, scrapeer_get_run_status, scrapeer_get_run_results, scrapeer_get_run_steps, scrapeer_list_runs, scrapeer_cancel_run, scrapeer_get_account, scrapeer_get_block_catalog, scrapeer_validate_flow, scrapeer_create_flow, scrapeer_update_flow, scrapeer_patch_flow


Codes to assign: desc_states_purpose, desc_states_when_to_use, desc_states_inputs, desc_names_side_effects, ambiguous_with.


## C019 — grants

Server: `dev.homespun/homespun`  Language: javascript/typescript

**Description (verbatim):**

> A v2 app


**Sibling tools (25):** deploy_app, list_rows, count_rows, get_row, upsert_row, update_row, delete_row, list_deleted_rows, restore_row, get_feed_events, apps, members, transfer, credentials, connections, ingest, attachments, taste, key, feedback, agent, community, publisher, review, get_skill


Codes to assign: desc_states_purpose, desc_states_when_to_use, desc_states_inputs, desc_names_side_effects, ambiguous_with.


## C020 — end_session

Server: `dev.hythe/hythe`  Language: javascript/typescript

**Description (verbatim):**

> Compatibility wrapper over checkpoint (Engram v1 B2, TOOL-COMPATIBILITY-MAP.md) — end_session IS checkpoint: pass {agentId, scope:{project|task}, expectedRevision, idempotencyKey, state, factChanges?, loopChanges?}. The legacy {projectId, summary, openItems} shape is RETIRED and returns a migration error. Legacy side effects are gone — the wrapper only checkpoints. Prefer checkpoint for new callers.


**Sibling tools (41):** mcp_latency, ws_fanout_latency, memory_read_latency, memory_write_latency, vector_fallback, availability, create_entities, add_observations, get_current_observation, compact_memory, create_relations, read_graph, get_entity_neighborhood, get_entity_backlinks, send_ai_message, get_ai_messages, register_agent, unregister_agent, gc_agent_registrations, set_agent_identity, get_agent_status, search_entities, discover_related_context, get_agent_context, begin_session


Codes to assign: desc_states_purpose, desc_states_when_to_use, desc_states_inputs, desc_names_side_effects, ambiguous_with.


## C021 — get_entity_detail

Server: `dev.hythe/hythe`  Language: javascript/typescript

**Description (verbatim):**

> Retrieve full entity content by storage ID, canonical entity name, or alias.


**Sibling tools (41):** mcp_latency, ws_fanout_latency, memory_read_latency, memory_write_latency, vector_fallback, availability, create_entities, add_observations, get_current_observation, compact_memory, create_relations, read_graph, get_entity_neighborhood, get_entity_backlinks, send_ai_message, get_ai_messages, register_agent, unregister_agent, gc_agent_registrations, set_agent_identity, get_agent_status, search_entities, discover_related_context, get_agent_context, begin_session


Codes to assign: desc_states_purpose, desc_states_when_to_use, desc_states_inputs, desc_names_side_effects, ambiguous_with.


## C022 — about

Server: `eu.ansvar/malawi-law-mcp`  Language: javascript/typescript

**Description (verbatim):**

> Server metadata, dataset statistics, freshness, and provenance.


**Sibling tools (12):** list_sources, search_legislation, get_provision, validate_citation, build_legal_stance, format_citation, check_currency, get_eu_basis, get_malawian_implementations, search_eu_implementations, get_provision_eu_basis, validate_eu_compliance


Codes to assign: desc_states_purpose, desc_states_when_to_use, desc_states_inputs, desc_names_side_effects, ambiguous_with.


## C023 — validate_eu_compliance

Server: `eu.ansvar/malawi-law-mcp`  Language: javascript/typescript

**Description (verbatim):**

> Check EU/international alignment status for a Malawian statute or provision.


**Sibling tools (12):** about, list_sources, search_legislation, get_provision, validate_citation, build_legal_stance, format_citation, check_currency, get_eu_basis, get_malawian_implementations, search_eu_implementations, get_provision_eu_basis


Codes to assign: desc_states_purpose, desc_states_when_to_use, desc_states_inputs, desc_names_side_effects, ambiguous_with.


## C024 — get_provision

Server: `eu.ansvar/pakistani-law-mcp`  Language: javascript/typescript

**Description (verbatim):**

> Retrieve the full text of a specific provision (section) from a Pakistani statute.


**Sibling tools (12):** about, list_sources, search_legislation, validate_citation, build_legal_stance, format_citation, check_currency, get_eu_basis, get_pakistani_implementations, search_eu_implementations, get_provision_eu_basis, validate_eu_compliance


Codes to assign: desc_states_purpose, desc_states_when_to_use, desc_states_inputs, desc_names_side_effects, ambiguous_with.


## C025 — list_sources

Server: `eu.ansvar/portuguese-law-mcp`  Language: javascript/typescript

**Description (verbatim):**

> Returns detailed provenance metadata for all data sources used by this server,


**Sibling tools (12):** about, search_legislation, get_provision, validate_citation, build_legal_stance, format_citation, check_currency, get_eu_basis, get_portuguese_implementations, search_eu_implementations, get_provision_eu_basis, validate_eu_compliance


Codes to assign: desc_states_purpose, desc_states_when_to_use, desc_states_inputs, desc_names_side_effects, ambiguous_with.
