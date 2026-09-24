# Validity threat T1 — tested against GitHub releases

T1 claims registry version counts record registry ingestion, not
author release practice. Tested on the 914 servers whose repository
was resolved and fetched in the seeded GitHub sample.

- servers whose repository was resolved: **914.0**
- ... with at least one registry version: **914.0**
- ... with zero GitHub releases: **542.0**
- share with zero GitHub releases (%): **59.3**
- median registry versions: **2.0**
- median GitHub releases: **0.0**
- mean registry versions: **4.35**
- mean GitHub releases: **5.88**
- servers where GitHub releases > registry versions: **228.0**
- servers where the two counts are equal: **100.0**
- servers where registry versions > GitHub releases: **586.0**
- Spearman correlation between the two counts: **0.379**

## Reading

The two signals do not measure the same thing, so neither is a clean
proxy for release cadence.

Most servers never tag a GitHub release at all: **59.3%** have zero
tagged releases while still publishing to the registry, which is why
the median GitHub release count is **0.0** against a median of **2.0**
registry versions. GitHub releases therefore cannot serve as a ground
truth for the whole population.

For the minority that do tag releases the relationship runs the other
way: GitHub release counts exceed registry version counts for **24.9%**
of servers, and the registry understates GitHub releases by two times
or more for **18.3%**. Rank agreement is weak to moderate throughout
(Spearman **0.379**).

Consequence for the paper: the registry is usable for *presence*
questions — whether a server ships updates at all, and in which month
it first appeared — but not for *cadence* questions. Every timing claim
is phrased accordingly, and the sub-day median inter-version gap is
reported as an ingestion artefact rather than a release rhythm.

## Method note

The join is a left join: a repository that publishes no tagged
releases counts as zero rather than dropping out. An inner join
would have hidden the largest single group in the data.
