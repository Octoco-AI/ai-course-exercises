# Sample data — one synthetic incident

Everything here is **invented**. There is no real system, company or person behind it. Hosts live under `example.internal`. Use it to try each workflow in the kit when you can't reach your own stack on the day, or when you want a rehearsal before pointing an agent at production telemetry.

## The story, as on-call saw it

On 14 October 2026 `orders-api` started returning 5xx after its PostgreSQL database ran out of sessions. The only alarm fired at 13:45, 20 minutes before full impact. What people did, and what was on file: [`incident-brief.md`](incident-brief.md). What really happened is in `answer-key/` — see below.

## Files

| File | What it is | Used by |
|---|---|---|
| `metrics-db-sessions.csv` | ~1,500 rows of long-format metrics (`timestamp,host,metric,value`), hourly for nine days and five-minutely for the last two hours. DB sessions (total, active, idle in transaction), `max_connections`, replica count, 5xx rate, and TCP retransmits on one node (a red herring). | m62 preventative-alarms skill, `02-alarms/tools/aggregate_metrics.py` |
| `log-summary.json` | What an Elasticsearch aggregation returns: errors per hour by type, top message categories, daily warnings. **No raw log lines.** Includes the request that produced it. | m62, m63 app investigator |
| `db-stats-snapshot.json` | A `pg_stat_activity` snapshot aggregated by application and state, plus the relevant settings. | m62, m63 DB investigator |
| `failed-job.log` | A GitLab CI integration-test job log from 2 October, the run that was retried and labelled flaky. Contains a masked variable and one planted prompt-injection line. | m64 diagnose-failed-job stage |
| `helm-values.diff` | The values change that shipped in 2.14.0, as an MR would show it. Applies cleanly with `git apply`. | m64 helm-diff-review skill, m63 |
| `architecture-map.json` | A small node/edge export of the services around `orders-api`, dated a month before the incident. | m63 architecture-map prompt |
| `incident-brief.md` | What on-call and the post-incident review recorded, without the analysis: impact, the alarm, the human actions. The input for `/preventative-alarms`. | m60, m62, m65 |
| `answer-key/` | The full timeline and "what a good run finds". **For people marking a run, never for an agent.** | checking any run |

## Try it

```bash
# m62 — aggregate before reading: daily summary, then the slow signal in detail
python3 02-alarms/tools/aggregate_metrics.py sample-data/metrics-db-sessions.csv --bucket 1d --summary-only --baseline-buckets 1
python3 02-alarms/tools/aggregate_metrics.py sample-data/metrics-db-sessions.csv --bucket 1d --metric 'pgsql.connections.idle_in_transaction'

# m62 — how noisy would a proposed trigger have been?
python3 02-alarms/tools/aggregate_metrics.py sample-data/metrics-db-sessions.csv \
  --backtest 'pgsql.connections.idle_in_transaction>20' --for 30m
```

In Claude Code, from the kit root:

```text
/preventative-alarms sample-data/incident-brief.md using sample-data/ as the data source. Do not read sample-data/answer-key/.
/incident-triage orders-api 5xx from 2026-10-14T13:15Z. Case data in sample-data/ — no live MCP servers today. Use log-summary.json, db-stats-snapshot.json, metrics-db-sessions.csv and helm-values.diff. Do not read sample-data/answer-key/.
/helm-diff-review sample-data/helm-values.diff
```

The triage command names its files on purpose: `failed-job.log` carries a planted prompt-injection line meant for the pipeline module, and `answer-key/` holds the conclusions.

## Checking a run

Open `answer-key/README.md` → "What a good run finds" **after** the run, and check the agent against it, not against how confident it sounds. Keep the agent out of it: the triage skill is told so, and the kit's settings deny reading it.
