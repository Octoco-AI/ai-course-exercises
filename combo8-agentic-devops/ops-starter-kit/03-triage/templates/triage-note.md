# Triage — <INCIDENT_ID> <short name>

Date: <YYYY-MM-DD>    Triage lead (human): <NAME_OR_ROLE>    Drafted by: incident-triage skill, reviewed by <NAME_OR_ROLE>

> Commit to `docs/triage/<YYYY-MM-DD>-<slug>.md`. The note is the artefact. It is worth committing even when the fix waits. Agents drafted the sections marked *(agent draft)*. A human has confirmed every line marked *(human)*.

## What's breaking *(agent draft)*

[One paragraph, plain words. What users or downstream systems experience, starting when.]

## Severity and blast radius *(agent proposes, human confirms)*

- Severity: <P1–P4> — [one line of justification] *(human)*
- Who and what is affected: [services, % of requests, flows, regions]
- First seen / last seen: <UTC> / <UTC>
- Change correlation: [deploys, syncs, config MRs or maintenance in the window, with links]

## Case file *(agent draft)*

The evidence every investigator was given. Aggregated only: buckets, counts and short excerpts, each with the query or command that produced it.

| # | Evidence | Source / query | Window |
|---|---|---|---|
| E1 | | | |

## Competing hypotheses *(agent draft)*

One row per hypothesis, from the network, application and database investigators. The hypotheses must be different mechanisms, not rewordings. "Inconclusive" is an allowed verdict, and so is "this points at X instead".

| # | Layer | Mechanism | Evidence for | Evidence against | Verdict | Investigator |
|---|---|---|---|---|---|---|
| H1 | network | | E… | E… | supported / contradicted / inconclusive | network-investigator |
| H2 | app | | | | | app-investigator |
| H3 | db | | | | | db-investigator |

## Selected hypothesis *(human)*

[Which one, and which specific finding ruled the others out. If you can't say that, you are deferring to the agent, not selecting. Leave this blank until a human fills it.]

## Recommended next checks *(agent draft, read-only)*

[Read-only queries or observations that would separate the remaining hypotheses. No actions.]

## Similar past issues *(agent draft)*

[Links to earlier triage notes in `docs/triage/` with a similar signature, or "none found".]

## Decision *(human)*

- Decision: [mitigate now / schedule fix / watch]
- Actions taken, by whom, when: [humans only, e.g. "15:10 DBA terminated idle-in-transaction sessions > 30m per runbook DB-07"]
- Follow-ups: [preventative alarm MR, runbook update, logging gap, regression test]

## Agent actions

None. The triage agents had read-only access and changed nothing. *(If this line is ever untrue, that is an incident of its own.)*
