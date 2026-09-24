# Threats to validity

Written before the results are final, so that each threat has a planned
mitigation rather than a retrospective excuse.

## Construct validity

**T1. Registry timestamps are not release dates.** `publishedAt` records when a
version entered the registry. Automation and bulk publishing make some gaps
sub-day, so "time between releases" measures registry activity, not engineering
cadence.

*Mitigation*: report the metric as "time between registry publications", show
the per-namespace distribution, and report results both with and without the
top namespaces. Compare registry versions against tagged GitHub releases for the
subset that has both.

**T2. Extraction coverage as a proxy for documentation quality.** A server whose
tools cannot be extracted is not necessarily undocumented; it may generate tools
at runtime or document them elsewhere.

*Mitigation*: the manual validation pass in `docs/codebook.md` Part A estimates
recall and the distribution of failure reasons. Recall is reported next to every
tool-level claim.

**T3. Secret-flagging is a publisher declaration.** A variable not marked
`isSecret` is not necessarily mishandled at runtime.

*Mitigation*: state the claim precisely — that clients cannot *automatically*
redact what the manifest does not flag — rather than claiming exposure.

## Internal validity

**T4. Registry-side validation filters.** The registry validates manifests, so
the absence of plaintext HTTP, bare-IP, and localhost endpoints is partly a
property of the registry, not of the ecosystem.

*Mitigation*: report this explicitly as a negative result about the registry's
gatekeeping, and do not present it as evidence of publisher discipline.

**T5. Duplicate or vendored servers.** A single implementation may appear under
several registry names.

*Mitigation*: report counts both by server name and by resolved repository; note
the difference rather than picking the flattering number.

**T6. Sampling drift.** The population grows while the study runs.

*Mitigation*: freeze the harvest at one date, record the cursor state and the
raw file digest, and state the population size at the freeze. All sampling draws
from the frozen snapshot.

## External validity

**T7. One registry, one protocol version.** The analysis covers one registry
during its first year. Findings may not transfer to other agent-tool ecosystems
(OpenAI tool schemas, LangChain tools, A2A).

*Mitigation*: describe the scope as the MCP registry, not "agent tooling", and
name the generalisation as future work with a concrete design.

**T8. Rapid change.** Conclusions about a fast-moving ecosystem age quickly.

*Mitigation*: state the freeze date everywhere, make the pipeline re-runnable so
a follow-up can repeat the study at a later freeze, and phrase claims as
properties of the window analysed.

## Conclusion validity

**T9. Version counts are heavy-tailed.** A handful of namespaces publish
thousands of versions, so means and totals are dominated by outliers.

*Mitigation*: report medians and the concentration table
(`t20_version_churn_concentration.csv`) alongside every mean. Never report a
mean version count without the median next to it.

**T10. Multiple comparisons.** Many group comparisons are reported.

*Mitigation*: treat all cross-source comparisons as descriptive associations,
avoid p-values, and say so in the method section.

## Reproducibility

**T11. Sources change or disappear.** Registries are mutable; packages get
unpublished.

*Mitigation*: store raw responses, record file digests, and ship a manifest so
the snapshot can be verified even after upstream changes.
