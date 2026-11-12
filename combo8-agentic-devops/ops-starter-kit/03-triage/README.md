# 03-triage — cross-stack incident triage (m63)

Three read-only investigators, one per layer (network, app, DB), work the same case file in parallel. Each returns competing hypotheses with evidence for and against. The `incident-triage` skill collects them into a **triage note** and stops there. Humans decide and act.

| Path | What it is |
|---|---|
| `templates/triage-note.md` | The artefact. Commit it to `docs/triage/` even when the fix waits |
| `templates/runbook.md` | One runbook per alarm class: Read (agent-safe), Decide, Act (humans only). Includes a worked example |
| `prompts/load-architecture-map.md` | Load a two-hop neighbourhood from a graph or CMDB export as context |
| `../.claude/skills/incident-triage/SKILL.md` | The orchestrating skill |
| `../.claude/agents/{network,app,db}-investigator.md` | The three read-only sub-agents |

## Guardrails

- No restarts, scaling, rollbacks, syncs or config changes. No acknowledging or silencing alarms.
- Investigators have no write tools: `Read`, `Grep`, `Glob` and the read-only MCP tools for their layer. That is an allowlist in each agent file. The tokens behind the MCP servers are read-only too (`01-access/`).
- No log dumps. Every piece of evidence is aggregated and cites its query.
- The skill stops at the triage note. Selecting the hypothesis and deciding what to do are human steps.

## Try it without a live stack

```text
/incident-triage orders-api 5xx from 2026-10-14T13:15Z. Case data in sample-data/ — no live MCP servers today. Use log-summary.json, db-stats-snapshot.json, metrics-db-sessions.csv and helm-values.diff. Do not read sample-data/answer-key/.
```

Afterwards — not before, and never through the agent — compare the note with `sample-data/answer-key/`. Did the network investigator rule out the retransmit spike with evidence, or just ignore it?
