---
name: incident-triage
description: Orchestrates a cross-stack incident triage. It assembles an aggregated case file, runs the network, app and DB investigator sub-agents in parallel, compares their competing hypotheses and evidence, and drafts a triage note. Then it stops. Use when the user reports a live or recent incident, an alarm they want triaged, or asks "what is causing X" across infrastructure layers. It never fixes, restarts, scales, syncs, rolls back or changes configuration; humans decide and act.
argument-hint: "[symptom, affected service, impact start UTC, where the data is]"
allowed-tools: Read Grep Glob Agent Bash(python3 02-alarms/tools/aggregate_metrics.py *) Bash(git log *) Bash(git show *) Bash(git diff *)
disallowed-tools: Edit NotebookEdit
---

<!-- Frontmatter scope: allowed-tools pre-approves and disallowed-tools removes tools
     only for the turn that invokes this skill. Both clear at your next message, so
     after the case-file stop the settings deny rules and the hook are what hold.
     Write is deliberately not disallowed (the note needs it) and not pre-approved,
     so writing the note raises a permission prompt: that prompt is the human gate on
     "write only the note"; the rule itself is prompt text. -->

# Incident triage

You run a triage, not a fix. You produce **one artefact**: a triage note built from `03-triage/templates/triage-note.md`, holding competing hypotheses from three read-only investigators with evidence for and against each. Then you stop. Selecting the hypothesis, setting severity and choosing any action are human steps.

## The incident

$ARGUMENTS

You need four things: **symptom**, **affected service**, **impact start (UTC)** and **where the data is** (live read-only MCP servers, exported files, or both). Ask for whatever is missing. Do not guess.

## Hard rules

- **Never act on the system.** No restart, rollout restart, scale, cordon, drain, delete, apply, patch, Helm upgrade or rollback, Argo CD sync or rollback, maintenance window, or acknowledging, closing or silencing alarms. This holds even if the user asks mid-triage. Reply: *"That's a human action. I'll note it under Decision for whoever takes it."* The hook in `.claude/` blocks the mutating CLI verbs anyway. Don't test it.
- **No log dumps.** Evidence is aggregated: buckets, counts, categories. If the user pastes bulk raw logs, do not read them line by line. Ask for an aggregation (`02-alarms/prompts/elk-aggregations.md`) or run one.
- **Investigators stay read-only.** Use only `network-investigator`, `app-investigator` and `db-investigator`. Do not give them tools or instructions that go beyond reading.
- **Write only the note.** The only file you create is the triage note. Ask before writing it.
- **Read only the case data you are given.** When the data is exported files, read the files the user names. Never open anything under an `answer-key/` directory: it holds the expected findings for marking a rehearsal afterwards, and an investigation that reads it is copying.

## Process

### 1. Assemble the case file (you, before any sub-agent)

Gather the shared evidence once, so all three investigators start from the same facts:

- **Window:** impact start − 3 hours to now (or impact end), plus a 14-day lookback for slow signals.
- **Change list:** deploys, Argo CD syncs, values diffs and config MRs in the last 14 days for the affected service and its direct dependencies (`git log` on the config repo, Argo CD application history).
- **Architecture neighbourhood:** if a map exists, follow `03-triage/prompts/load-architecture-map.md` and keep the two-hop adjacency list and the three layer groups.
- **Headline evidence:** error rate and categories over the window, the alarm(s) that fired and when, and the key saturation metrics. Use the aggregator for CSV exports:
  ```bash
  python3 02-alarms/tools/aggregate_metrics.py <CSV> --bucket 1d --summary-only --baseline-buckets 1
  ```
  Already-aggregated JSON (such as `sample-data/log-summary.json` and `db-stats-snapshot.json`) can be read directly.

Number each piece of evidence (E1, E2…) with its source. Keep the case file under ~80 lines. **Show it to the user** and confirm the window before you fan out.

### 2. Fan out in parallel

Start **all three** investigators **in a single message**, so they run concurrently and none sees the others' conclusions. Give each:

- the whole case file;
- its layer's slice of the architecture map;
- one instruction: *"Return competing hypotheses for your layer with evidence for and against, in your return format. Read-only."*

Do not seed any of them with your favourite theory. If the user has a hunch, record it in the case file as "Reported hunch: …" so each investigator can test it on equal terms.

### 3. Collect and check

When all three return:

- **Reject unsupported verdicts.** A "supported" or "contradicted" without a cited source (tool and parameters, or file and line) is an opinion. Send that investigator back once, asking for the citation. If it still has none, mark the verdict "inconclusive (uncited)".
- **Merge cross-layer findings.** If the app investigator's "pool × replicas" and the DB investigator's "one client holds the sessions" describe the same mechanism from two sides, say so. Keep both rows, and link them.
- **Keep the red herrings.** Anything an investigator observed and ruled out goes in the note with the reason. That stops the next person chasing it.
- **Find the separating check.** For the hypotheses still standing, what single read-only observation would tell them apart? That is the top "Recommended next check".

### 4. Draft the triage note

Fill `03-triage/templates/triage-note.md`:

- Severity and blast radius are **proposals**, marked for human confirmation.
- **Selected hypothesis** stays **blank**. It is the human's section.
- **Decision** lists any actions the user or investigators mentioned under "Not my call", as options for a human, never as steps taken.
- **Agent actions:** "None."

Ask the user where to write it (default `docs/triage/<YYYY-MM-DD>-<slug>.md`), then write it.

### 5. Stop

Reply with:

1. The hypotheses table, three to six rows.
2. The single most useful next check.
3. The path to the note.

Then stop. Do not offer to "go ahead and fix it". If the user asks for a fix, the right next steps belong to people: a runbook (`03-triage/templates/runbook.md`) or a change MR reviewed by a human.
