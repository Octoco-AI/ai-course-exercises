# Runbook — <ALARM_CLASS> (<RUNBOOK_ID>)

Owner: <TEAM>    Last exercised: <YYYY-MM-DD>    Linked triggers: <TRIGGER_NAMES_OR_UIDS>    Self-heal policy: <link or "none">

> One runbook per alarm class, not per trigger. Keep it in the repo next to the triggers it serves, so a trigger MR and a runbook MR can be reviewed together. Agents may **read** this runbook and quote it in a triage note. Every step under **Act** is for a human unless a self-heal policy (`05-self-heal/`) names it explicitly.

## Symptoms

- What fires: [trigger names, severity, audience]
- What users see: [errors, latency, which flows]
- What it is often confused with: [the usual red herrings]

## Read — establish the facts

Read-only checks, aggregated. Each has the exact query or command, and what "normal" looks like.

| # | Check | Command / query | Normal | Bad looks like |
|---|---|---|---|---|
| R1 | | | | |
| R2 | | | | |

An agent can run these through the read-only MCP servers, or the `incident-triage` skill can run them for you.

## Decide

```
R1 bad? ── no ──▶ not this class; see <OTHER_RUNBOOK>
   │yes
R2 shows <X>? ── yes ──▶ Act A1
   │no
   └──▶ Act A2, and escalate to <TEAM>
```

## Act — humans only

Each action states its blast radius, who may do it, and how to undo it. Destructive steps are marked **[D]** and need the named confirmation from `05-self-heal/destructive-actions.md`.

| # | Action | Command | Blast radius | Who | Confirm with | Undo |
|---|---|---|---|---|---|---|
| A1 | | | | on-call | | |
| A2 [D] | | | | <ROLE> | <ROLE> | |

## Rollback

[How to return to the last known good state: usually a revert MR in the config repo, then a human-approved sync.]

## Escalation

- First: <ROLE / ROTA>, within <MINUTES>
- Then: <ROLE / ROTA>
- Vendor or other team: <CONTACT ROUTE>

## After

- [ ] Triage note committed (`03-triage/templates/triage-note.md`)
- [ ] Preventative-alarm review scheduled (`/preventative-alarms`)
- [ ] This runbook updated with whatever was missing or wrong

---

## Worked example (synthetic) — database session exhaustion, DB-07

| # | Check | Command / query | Normal | Bad looks like |
|---|---|---|---|---|
| R1 | Sessions against the usable limit | Zabbix item `pgsql.connections.total` vs `{$PG.SESSIONS.LIMIT}` | < 70 % | ≥ 85 % sustained |
| R2 | Sessions by application and state | Query 1 in `02-alarms/prompts/db-stats.md` | idle-in-transaction < 10 | one application holds dozens of idle-in-transaction sessions, oldest hours or days old |
| R3 | Recent change to that application | Argo CD app history; `git log` on its values file | nothing in 7 days | pool size, replica ceiling or timeout changed |

| # | Action | Blast radius | Who | Confirm with | Undo |
|---|---|---|---|---|---|
| A1 [D] | Terminate idle-in-transaction sessions older than 30 minutes for the offending application only (`pg_terminate_backend` over a filtered `pg_stat_activity`) | Those transactions roll back | on-call DBA | incident lead | none; the transactions are gone, so the application must retry |
| A2 | Revert MR for the suspect values change; human approves the Argo CD sync | The one application | on-call ops | MR approver | revert the revert |
