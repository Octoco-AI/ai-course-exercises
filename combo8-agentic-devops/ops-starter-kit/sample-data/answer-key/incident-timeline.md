# Incident timeline — orders database out of sessions (synthetic)

> Invented for the workshop. Every host lives under `example.internal`; the
> service, the people and the numbers are made up. Times are UTC.

**Summary.** `orders-api` started returning 5xx on 14 October 2026 because the
PostgreSQL database `ordersdb` on `db01.example.internal` ran out of client
sessions (`max_connections = 300`, 3 reserved for superusers). The fast signal
fired 20 minutes before full impact. The slow signal — sessions stuck
`idle in transaction` — had been climbing for seven days and nothing watched it.

| When (UTC) | What happened | Source |
|---|---|---|
| 2026-10-02 11:40 | MR pipeline for the CSV-export feature: `integration-test` fails with a HikariCP leak warning. Retried, passes, labelled "flaky", merged. | `failed-job.log` |
| 2026-10-05 09:30 | Argo CD syncs `orders-api` 2.14.0 to production. Values change: pool 10 → 30 per pod, HPA max 6 → 10, leak detection switched off. | `helm-values.diff` |
| 2026-10-05 09:30 → | `pgsql.connections.idle_in_transaction` begins a steady climb of roughly 9 sessions a day. | `metrics-db-sessions.csv` |
| 2026-10-07 10:00 | Idle-in-transaction sessions pass 20 and, from 10-08 05:00, never drop back. No trigger watches this item. | `metrics-db-sessions.csv` |
| 2026-10-12 02:00–04:00 | TCP retransmits spike on `k8s-node-03.example.internal` during a planned kernel patch and reboot. Unrelated. | `metrics-db-sessions.csv` |
| 2026-10-13 | Daily peak of total sessions reaches 266 of 297 usable. Nobody looks. | `metrics-db-sessions.csv` |
| 2026-10-14 13:15 | Total sessions hit 297. Sporadic `too many clients` errors; 5xx at ~0.7 %. | metrics, `log-summary.json` |
| 2026-10-14 13:45 | Existing Zabbix trigger fires: *PostgreSQL sessions ≥ 95 % of max for 30m* (HIGH). On-call paged. | Zabbix |
| 2026-10-14 14:05 | Full impact: 5xx at 15–20 %. Checkout degraded. | metrics, `log-summary.json` |
| 2026-10-14 14:10 | DBA takes a `pg_stat_activity` snapshot, aggregated by application and state. | `db-stats-snapshot.json` |
| 2026-10-14 14:20 | Incident declared, severity P2. | incident channel |
| 2026-10-14 15:10 | **Human action:** on-call DBA terminates `idle in transaction` sessions older than 30 minutes (runbook DB-07). 5xx drops below 1 %. | runbook |
| 2026-10-14 15:25 | **Human action:** revert MR in the config repo rolls `orders-api` back to 2.13.4; a human approves the sync in Argo CD. | config repo |

## What the workshop does with this

- **m62** — find the slow signal and propose triggers that would have fired on 10-07, not 10-14.
- **m63** — run three investigators (network, app, DB) against the same case file and compare competing hypotheses. The retransmit spike is a genuine red herring.
- **m64** — the 10-02 pipeline log already contained the root cause. Would a diagnose-failed-job stage have caught it? Would the Helm diff review have flagged 30 × 10 = 300 against `max_connections = 300`?
- **m65** — design, on paper, which part of the response an agent could ever be allowed to do. (Terminating sessions is on the destructive-actions list. Opening a revert MR is not.)
