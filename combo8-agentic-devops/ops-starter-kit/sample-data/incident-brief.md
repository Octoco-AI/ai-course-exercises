# Incident brief — orders-api 5xx, 14 October 2026 (synthetic)

> Invented for the workshop. Every host lives under `example.internal`; the
> service, the people and the numbers are made up. Times are UTC.
>
> This is what the on-call engineer and the post-incident review recorded, **without
> the analysis**. It is the input for `/preventative-alarms` and the fallback for the
> exercises that need an incident to work from. The full timeline and the expected
> findings are in `answer-key/`: they are for checking a run afterwards, never for
> handing to an agent.

**Impact.** From 13:15 on 14 October 2026, `orders-api` returned sporadic 5xx. At
14:05 it reached 15–20 % of requests and checkout was degraded. Error rate back
below 1 % at 15:10.

**Affected.** `orders-api` (namespace `orders`, cluster `k8s-prod.example.internal`) and the
PostgreSQL database `ordersdb` on `db01.example.internal`.

**The alarm that fired.** 13:45, Zabbix: *PostgreSQL sessions ≥ 95 % of max for
30m* (HIGH). On-call was paged. The review recorded that monitoring worked: the
alarm fired.

## What people did

| When (UTC) | Action | Who |
|---|---|---|
| 2026-10-02 11:40 | An `integration-test` job on the CSV-export MR failed. Retried, passed, labelled "flaky"; the MR was merged. | Developer |
| 2026-10-05 09:30 | `orders-api` 2.14.0 synced to production by Argo CD after a reviewed values MR. | Release engineer |
| 2026-10-14 13:45 | Answered the sessions page. | On-call engineer |
| 2026-10-14 14:10 | Took a `pg_stat_activity` snapshot, aggregated by application and state. | DBA |
| 2026-10-14 14:20 | Declared the incident, severity P2. | Incident lead |
| 2026-10-14 15:10 | Terminated `idle in transaction` sessions older than 30 minutes (runbook DB-07). | DBA |
| 2026-10-14 15:25 | Merged a revert MR rolling `orders-api` back to 2.13.4 and approved the Argo CD sync. | On-call engineer and a reviewer |

## The question the review left open

Could anything have warned us earlier than 13:45, and what would the alarm have
been?

## Data on file

The exported, already-aggregated data is in this directory: `metrics-db-sessions.csv`,
`log-summary.json`, `db-stats-snapshot.json`, `helm-values.diff`,
`architecture-map.json` and `failed-job.log` (see `README.md`).
