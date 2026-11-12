---
name: ops-grafana
description: Query Grafana read-only through mcp-grafana with --disable-write — find dashboards, read alert rules, and run aggregated Prometheus and Loki queries over a bounded time range. Use when the user asks what a metric did around an incident, which panel shows something, what an alert rule checks, or for a deeplink to share.
allowed-tools: mcp__grafana__search_dashboards mcp__grafana__search_folders mcp__grafana__get_dashboard_summary mcp__grafana__get_dashboard_property mcp__grafana__list_datasources mcp__grafana__get_datasource mcp__grafana__query_prometheus mcp__grafana__list_prometheus_metric_names mcp__grafana__list_prometheus_label_values mcp__grafana__query_loki_logs mcp__grafana__list_loki_label_names mcp__grafana__list_loki_label_values mcp__grafana__alerting_rules_read mcp__grafana__get_annotations mcp__grafana__list_incidents mcp__grafana__get_incident mcp__grafana__generate_deeplink
---

# Grafana, read-only

You act as a Viewer service account and the server runs with `--disable-write`.
You can search, read and query. You cannot edit dashboards, alert rules, silences,
annotations, incidents or snapshots.

## Before the first query

1. Confirm the **time range**: incident time ± 30 minutes unless told otherwise.
   Every query states start and end explicitly.
2. Find the **datasource** once (`list_datasources`) and the right **dashboard**
   (`search_dashboards`), then `get_dashboard_summary` — not the full dashboard JSON
   — to see which panels and queries exist. Reuse a panel's query rather than
   inventing one.

## Query well

- **PromQL: aggregate in the query.** Ask for a handful of series, not thousands:
  `sum by (service) (rate(http_requests_total{code=~"5.."}[5m]))`,
  `histogram_quantile(0.95, sum by (le, service) (rate(http_request_duration_seconds_bucket[5m])))`.
  Use a step that gives about 60–120 points for the window. Check label values with
  `list_prometheus_label_values` before filtering on them.
- **LogQL: metric queries first.** `sum by (app) (count_over_time({namespace="web"} |= "error" [1m]))`
  shows when errors started. Read raw lines only for one stream, with a small
  limit, after you know the minute that matters.
- **Alert rules.** `alerting_rules_read` to quote what a rule evaluates, its
  threshold, `for` duration and labels. Compare the rule's query to the metric's
  actual behaviour in the window — that is how you find a rule that could not fire.
- **Annotations** for the window often show deploys; line them up with the change
  in the metric.

## Never

- Never create or change a dashboard, alert rule, contact point, silence,
  annotation, folder, incident or snapshot. Draft a proposed rule as JSON for an MR
  in the config repo instead.
- Never run a query without a time range, or one that returns raw high-cardinality
  series (no `by (pod, container, instance)` across a whole cluster).
- Never shorten a deeplink (`shorten=true` writes to Grafana); share the long link.

## Hand back

The metric's behaviour in numbers (baseline, peak, time of peak, when it returned
to normal), the queries you ran, the alert rule that should have caught it and
why it did or did not fire, and a deeplink to the panel and time range.
