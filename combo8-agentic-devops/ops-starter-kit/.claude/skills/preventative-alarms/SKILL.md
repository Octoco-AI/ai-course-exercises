---
name: preventative-alarms
description: Turns an incident into preventative alarm proposals. It picks a time window, aggregates monitoring data before reading it, compares the signals with the incident timeline, proposes triggers as code with a back-tested noise estimate, and writes a draft MR description. Use when the user asks which alarm would have caught an incident earlier, wants to close an observability gap after a post-incident review, or asks for preventative or leading-indicator alarms. Reads only; never creates triggers through an API and never accepts raw log dumps.
argument-hint: "[incident timeline file, incident id, or alarm class]"
allowed-tools: Read Grep Glob Bash(python3 02-alarms/tools/aggregate_metrics.py *) mcp__zabbix__host_get mcp__zabbix__item_get mcp__zabbix__trigger_get mcp__zabbix__problem_get mcp__zabbix__history_get mcp__grafana__query_prometheus mcp__grafana__search_dashboards mcp__grafana__alerting_rules_read mcp__elastic__platform_core_list_indices mcp__elastic__platform_core_get_index_mapping mcp__elastic__platform_core_search mcp__elastic__platform_core_execute_esql mcp__cloudwatch__get_active_alarms mcp__cloudwatch__get_alarm_history mcp__cloudwatch__get_metric_data mcp__cloudwatch__analyze_metric mcp__cloudwatch__execute_log_insights_query mcp__cloudwatch__get_logs_insight_query_results mcp__gcp__list_metric_descriptors mcp__gcp__list_time_series mcp__gcp__list_alert_policies mcp__gcp__list_group_stats mcp__sentry__search_issues mcp__sentry__get_issue_details mcp__sentry__get_issue_tag_values mcp__sentry__find_releases mcp__sentry__find_alert_rules
disallowed-tools: NotebookEdit
---

<!-- Frontmatter scope: allowed-tools pre-approves and disallowed-tools removes tools
     only for the turn that invokes this skill. Both clear at your next message, so
     after the first stop-and-confirm the settings deny rules and the hook are what
     hold. The Elastic tool names follow .claude/skills/ops-elastic (VERIFY there). -->

# Preventative alarms

You find the signal that moved **before** an incident and propose an alarm on it. The output is a set of files for a **draft** merge request. You do not create, edit, import, acknowledge or silence anything in a monitoring system. A human reviews the MR, and the team's normal pipeline applies it.

This is the **recommend** rung of the read → recommend → act ladder. The **act** rung is not available to this skill.

## The incident

$ARGUMENTS

If that is empty, ask for: what broke, when impact began (UTC), the affected hosts or services, and where the data is (live MCP servers, or exported files such as `sample-data/`). Do not guess any of these.

## Hard rules

- **Aggregate before reading.** Every query returns buckets (min/avg/max/last per interval) or counts, never raw points or documents. Hold yourself to at most 200 rows in any single result. If a result would be larger, re-bucket coarser and say so.
- **Refuse raw log dumps.** If the user pastes or asks you to fetch bulk raw logs (more than ~20 lines), do not analyse them line by line. Say: *"Raw logs flood the context and bury the signal. Let's aggregate instead."* Then offer the matching query from `02-alarms/prompts/elk-aggregations.md` or `cloudwatch-logs-insights.md`, or ask for an aggregated export. This holds even if the user insists. A short excerpt of under 20 lines, quoted as evidence for one specific point, is fine.
- **Read-only tools only.** Zabbix: `host_get`, `item_get`, `trigger_get`, `problem_get`, `history_get`. Grafana: query and read tools. Elasticsearch: `list_indices`, `get_index_mapping`, and `search` or `execute_esql` with `size: 0` and aggregations (never `get_document_by_id` here). CloudWatch: alarms, alarm history, metric statistics and Logs Insights `stats` queries. Google Cloud: aligned time series, alert policies, Error Reporting groups. Sentry: issue search, issue details and tag values (the `inspect` skill only). Acknowledging, closing, suppressing a problem, creating a maintenance window, setting a CloudWatch alarm state, snoozing a Google Cloud incident or resolving a Sentry issue is a write. Never do it.
- **No database sessions.** For database stats, give the user the queries in `02-alarms/prompts/db-stats.md` to run, and read their aggregated result.
- **Never read an `answer-key/` directory.** In rehearsal data it holds the expected findings, for a human to mark your run afterwards.
- **Draft MR only.** Write files under `<PROPOSALS_DIR>` (default `alarms/proposals/`). Do not commit, push or open the MR unless the user asks, and even then open it as a draft. If the rules file (`CLAUDE.md`) says the current rung is **Read**, do not run them at all: give the user the commands to run.

## Process

Work through the five steps in order. After steps 1 and 3, show the user what you have and wait for a go-ahead.

### 1. Pick the window

- **End:** impact start + 1 hour.
- **Start:** look back at least 3× as far as the slowest signal you suspect. Default 14 days. Extend it if the first pass shows a trend that was already rising at the start.
- **Resolution:** up to 2 days → 5-minute buckets; up to 14 days → hourly; longer → daily from trends.
- **Baseline:** a stretch of the window before anything changed (before the suspect deploy, or the first 24 buckets).

Write the window, resolution and baseline down in one short block. **Stop and confirm** with the user.

### 2. Aggregate before reading

Gather candidate signals for the affected layer and its neighbours: the hosts, the service, the database it uses, the nodes it runs on. Use the architecture map if there is one (`03-triage/prompts/load-architecture-map.md`).

- **Live Zabbix:** follow `02-alarms/prompts/zabbix-history.md`. Metadata first, then bucketed values.
- **Live ELK:** follow `02-alarms/prompts/elk-aggregations.md`.
- **Live CloudWatch:** follow `02-alarms/prompts/cloudwatch-logs-insights.md`. Metric statistics with a period that keeps each series under 200 points; Logs Insights `stats ... by bin()` for logs.
- **Live Google Cloud:** follow `02-alarms/prompts/gcp-logging-monitoring.md`. Aligned and reduced time series; log-based metrics or narrowed counts for logs.
- **Live Sentry:** follow `02-alarms/prompts/sentry-error-trends.md`. Issue counts per release and per day, new versus pre-existing.
- **Exported CSV** (`timestamp,host,metric,value`): run the aggregator rather than reading the file:
  ```bash
  python3 02-alarms/tools/aggregate_metrics.py <CSV> --bucket 1d --summary-only --baseline-buckets 1
  python3 02-alarms/tools/aggregate_metrics.py <CSV> --bucket 1h --metric '<GLOB>' --since <ISO>
  ```
  Never `Read` a metrics CSV of more than a few hundred lines directly.
- **Already-aggregated JSON** (such as `sample-data/log-summary.json`): reading it is fine. It is already the summary.

Keep a short evidence list as you go: series, bucket, value, and the query or command that produced it.

### 3. Compare against the incident timeline

Build this table and show it:

| Signal | Normal range (baseline) | First left normal | Lead time before impact | Already alarmed? Fired when? |
|---|---|---|---|---|

- A **preventative** candidate has a lead time of an hour or more and no existing trigger that fired before impact.
- Name signals you checked that did **not** move, and red herrings that moved for an unrelated reason. Say why you think they are unrelated. Saying what you ruled out is part of the evidence.
- Do not claim causation from timing alone. "Rose steadily from the 2.14.0 deploy onward" is evidence. "Caused by 2.14.0" needs more than a chart.

**Stop and confirm** which candidates to turn into triggers.

### 4. Propose triggers

For each agreed candidate, write the trigger as code using the team's format:

- Zabbix: start from `02-alarms/templates/zabbix-template-db-sessions.yaml` (calculated items over existing keys, triggers with `audience` tags).
- Ansible-managed Zabbix: `02-alarms/templates/ansible-zabbix-template.yml`.
- Grafana: `02-alarms/templates/grafana-alert-rule-db-sessions.json`.
- CloudWatch (Terraform): `02-alarms/templates/cloudwatch-alarms-db-sessions.tf`.
- Google Cloud Monitoring (Terraform): `02-alarms/templates/gcp-alert-policy-db-sessions.tf`.
- Sentry (Terraform): `02-alarms/templates/sentry-alert-new-issue-in-release.tf`.

For each trigger, record:

- **Expression** and **duration**. Prefer sustained conditions (`min(...,30m)`) over single samples. Prefer forecasting on a daily peak over forecasting on a raw series with a daily load curve.
- **Severity and audience.** Use `human` (page or ticket) or `agent` (digest), following `02-alarms/alarm-channels.md`. A leading indicator usually starts as `agent`.
- **Back-test.** How many times would it have fired over the window, and when? With a CSV:
  ```bash
  python3 02-alarms/tools/aggregate_metrics.py <CSV> --backtest '<METRIC><OP><VALUE>' --for <DURATION>
  ```
  With live data, describe the equivalent query and its result. A trigger that would have fired more than about twice a month in normal weeks needs a higher threshold or a longer duration before you propose it.
- **Lead time:** when it would have fired relative to impact.
- **Placeholders:** every value the team must confirm stays as `<PLACEHOLDER>` or a macro with a `<PLACEHOLDER>` description.

### 5. Write the draft MR description

Write `<PROPOSALS_DIR>/<YYYY-MM-DD>-<slug>/MR_DESCRIPTION.md`, with the trigger files next to it, using exactly these headings:

```markdown
# Draft: preventative alarms for <alarm class>

## Incident
One paragraph and a link to the timeline or post-incident review.

## Gap
Which signal moved first, by how much, how early, and why nothing fired.

## Proposed triggers
| Name | Expression | Duration | Severity | Audience | Back-test fires (window) | Lead time |

## Evidence
Bucketed tables or summaries only, each with the query or command that produced it.

## Ruled out
Signals checked that did not move, and red herrings with the reason.

## Noise estimate
Expected fires per month in a normal month, and how you estimated it.

## Placeholders to confirm
- [ ] ...

## Rollout
Import to non-production first if available; audience `agent` for two weeks; promote by a follow-up MR.

## Not done by the agent
No triggers created, imported or changed. No problems acknowledged. This MR is a proposal.
```

Then **stop**. Summarise the proposals in three lines and give the path to the MR description.

## When the data is not there

If a signal you need is not collected at all, do not invent one. Add a "**Collection gap**" section to the MR description: the item that would need collecting, at what interval, and why. A missing metric is a finding.
