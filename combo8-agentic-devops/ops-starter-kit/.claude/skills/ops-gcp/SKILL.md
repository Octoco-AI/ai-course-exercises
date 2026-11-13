---
name: ops-gcp
description: Investigate Google Cloud read-only — Cloud Logging, Cloud Monitoring time series and alert policies, Error Reporting groups and Cloud Trace — through the Google Cloud Observability MCP server or gcloud read verbs, as a viewer service account. Use when the user asks why a Google Cloud alert fired, which errors spiked in Cloud Logging, what a Cloud Run, GKE or Cloud SQL metric did around an incident, or what changed in a service.
allowed-tools: mcp__gcp__list_log_names mcp__gcp__list_log_entries mcp__gcp__list_metric_descriptors mcp__gcp__list_time_series mcp__gcp__list_alert_policies mcp__gcp__list_traces mcp__gcp__get_trace mcp__gcp__list_group_stats Bash(gcloud config get-value *) Bash(gcloud logging read *) Bash(gcloud monitoring policies list *) Bash(gcloud run services describe *) Bash(gcloud run revisions list *) Bash(gcloud sql instances describe *) Bash(gcloud container clusters describe *) Bash(gcloud builds list *)
---

# Google Cloud, read-only

You act as the `ops-reader` service account, by impersonation, with
`logging.viewer`, `monitoring.viewer`, `errorreporting.viewer` and the per-service
viewer roles in `01-access/token-checklist.md`. You cannot deploy, update, restart,
resize or delete anything, read secrets, or print access tokens. The observability
MCP server only lists and reads, and the hook blocks mutating `gcloud` and `gsutil`
commands. If you are blocked, that is the design working.

<!-- VERIFY: tool names against the @google-cloud/observability-mcp version you pin
     (`/mcp` lists them). The template keys the server as `gcp`. -->

## Before the first query

1. Confirm the **project** (`gcloud config get-value project`, or the
   `GOOGLE_CLOUD_PROJECT` the server runs with) and say which one you are on. If it
   is not the one the user meant, stop. Logging calls work on one project at a time.
2. Confirm the **time window** in UTC: the incident ± 30 minutes unless told
   otherwise. Every log filter carries a `timestamp>=` and `timestamp<` clause.
3. Name the **resource**: `resource.type` and its labels (`cloud_run_revision` with
   `service_name`, `k8s_container` with `namespace_name`, `cloudsql_database` with
   `database_id`). Never filter on severity alone across the project.

## Query well

- **Error Reporting first.** `list_group_stats` for the window: which error groups
  are new, which grew, and their first-seen time. That is already an aggregation.
- **Metrics as aligned time series, never raw points.** `list_time_series` with an
  aligner and an alignment period that keeps the result under ~200 points
  (`ALIGN_MAX` or `ALIGN_PERCENTILE_99`, 1 h for 7 days, 5 min for 6 hours), and a
  reducer across instances where you want one line per service. Useful types:
  `run.googleapis.com/request_count` by `response_code_class`,
  `run.googleapis.com/request_latencies`,
  `cloudsql.googleapis.com/database/postgresql/num_backends`,
  `kubernetes.io/container/restart_count`.
- **Logs: counts before lines.** Cloud Logging has no aggregation in `list_log_entries`,
  so count by narrowing: one filter per error class with a small `pageSize`, or use
  a log-based metric that already exists and read it as a time series. The shapes are
  in `02-alarms/prompts/gcp-logging-monitoring.md`. Read at most five entries for
  one specific error.
- **What changed.** Cloud Run: `gcloud run revisions list --service <SERVICE>`
  (creation times, traffic split, image). GKE: workload events from the Kubernetes
  skill. Admin Activity audit log over the window
  (`logName:"cloudaudit.googleapis.com%2Factivity"`), summarised as who, which
  method, which resource, when.
- **Alert policies** with `list_alert_policies`: what exactly the policy that fired
  checks, and what it does not.

## Never

- Never run a create, update, deploy, patch, set, delete, restart, resize or
  `ssh` command — and never ask for the hook to be relaxed.
- Never print credentials: `gcloud auth print-*`, `secrets versions access`,
  `container clusters get-credentials`, `config config-helper`.
- Never query logs without a time range or a resource filter, and never print
  `httpRequest`, `jsonPayload` user fields or request bodies in bulk: they hold
  personal data.
- Never change the active project or account (`gcloud config set`).

## Hand back

A triage note: project, resource, region; what is unhealthy and since when; the
evidence (error groups with counts and first-seen, time series with aligner and
period, log filters with their counts, recent revisions or audit events); the most
likely cause and how sure you are; and the recommended change as an MR to the IaC
or service config that owns it — "set `max-instances` to 6 in
`deploy/orders-api.service.yaml`", not "I updated the service".
