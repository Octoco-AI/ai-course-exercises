---
name: ops-sentry
description: Investigate application errors read-only in Sentry — issues, their frequency and first-seen release, tag distributions, stack traces, traces and release health — through the Sentry MCP server with only the inspect skill. Use when the user asks which errors started with a release, what an issue's blast radius is, whether a spike is new or old, or what Sentry shows around an incident.
allowed-tools: mcp__sentry__whoami mcp__sentry__find_organizations mcp__sentry__find_projects mcp__sentry__find_releases mcp__sentry__get_release_details mcp__sentry__search_issues mcp__sentry__get_issue_details mcp__sentry__get_issue_tag_values mcp__sentry__get_issue_activity mcp__sentry__get_event_stacktrace mcp__sentry__get_issue_breadcrumbs mcp__sentry__search_issue_events mcp__sentry__search_errors mcp__sentry__get_trace_details mcp__sentry__get_span_details mcp__sentry__find_alert_rules mcp__sentry__get_alert_rule
---

# Sentry, read-only

You act with a user auth token scoped `org:read`, `project:read`, `team:read`,
`event:read`, through the Sentry MCP server started with `--skills inspect`. You
cannot resolve, ignore, assign or comment on issues, or change alert rules,
monitors, projects or DSNs. Those tools are not offered and are denied in the
settings. Do not try them.

<!-- VERIFY: tool names against the @sentry/mcp-server version you pin (`/mcp`
     lists them). Some search_* tools translate natural language with an embedded
     model and need an LLM API key on the server; without one, pass Sentry search
     syntax (`is:unresolved firstSeen:-24h`) or use get_issue_details. -->

## Before the first query

1. `whoami` and `find_projects`: say which **organisation and project** you are on.
   If the server was pinned to one (`--org`, `<org>/<project>`), stay inside it.
2. Confirm the **environment** (`production`, `staging`) and the **time window** in
   UTC. Every search states both.
3. Find the **release** that was live: `find_releases` for the project, ordered by
   date, and note which release was deployed when impact began.

## Query well

- **Issues, not events.** Start with `search_issues` for the window and environment,
  sorted by frequency: title, culprit, event count, user count, `firstSeen`,
  `lastSeen`. Ten issues is a lot. Mark each one **new** (first seen in the window
  or in the live release) or **pre-existing** (seen weeks before at a similar rate).
  A noisy pre-existing issue is rarely the cause.
- **Blast radius from tags.** `get_issue_tag_values` for `release`, `environment`,
  `server_name` or `transaction`, `url`, `browser`: one release, one host, one
  endpoint? That is the evidence, as counts.
- **One stack trace, summarised.** `get_event_stacktrace` for the latest event of
  the top new issue: exception type and message, the first in-app frame
  (`path:line`), and what it calls next (database, HTTP, queue). Breadcrumbs only for
  the few lines before the error.
- **Release health.** `get_release_details` for the live release against the one
  before it: new issues, crash-free rate, adoption. "Errors started with release X"
  needs both sides.
- **Traces** for latency questions: one slow trace, its slowest spans and their
  operation (`db`, `http.client`), not every span.
- **Alert rules** with `find_alert_rules`: did a rule exist for this issue, and why
  did or didn't it fire?

## Never

- Never resolve, ignore, archive, merge, assign or comment on an issue, and never
  create, edit or delete an alert rule or monitor — "just tidying up" included.
- Never start a Seer analysis: it is not in the inspect skill, and it is billed.
- Never print user identifiers, emails, IP addresses, cookies, headers or request
  bodies from an event. Count by them or leave them out.
- Never page through every event of an issue. Issue counts and tag values are
  already aggregated.

## Hand back

A triage note: organisation, project, environment, release; the new issues with
counts, users affected and first-seen time; the tag evidence (which release, host,
endpoint); one summarised stack trace with its first in-app frame; release-health
deltas; the most likely cause and how sure you are; and the recommended change as
an MR or a ticket — "revert the pool-size change in `values-prod.yaml`", or
"ticket for the app team with issue link and frame" — not "I resolved the issue".
