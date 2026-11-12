# 02-alarms — observability gaps to preventative alarms (m62)

After an incident, find the signal that moved first and propose an alarm on it, as code, in a draft MR. The workflow is the `preventative-alarms` skill in `.claude/skills/`. This directory holds what it uses.

| Path | What it is |
|---|---|
| `prompts/zabbix-history.md` | Query Zabbix history through the read-only MCP server: metadata first, then bucketed values |
| `prompts/elk-aggregations.md` | Elasticsearch aggregations (query DSL and ES\|QL) with `size: 0`. Never raw logs |
| `prompts/db-stats.md` | PostgreSQL (and MySQL) session and limit queries that aggregate in SQL and never select query text |
| `prompts/alarm-noise-review.md` | Monthly review that classifies existing triggers into keep, tune, re-route or delete |
| `templates/zabbix-template-db-sessions.yaml` | Trigger proposal as a Zabbix template: calculated items over your existing keys, sustained and forecast triggers, `audience` tags |
| `templates/ansible-zabbix-template.yml` | The same template imported by Ansible (`community.zabbix`) |
| `templates/grafana-alert-rule-db-sessions.json` | The same three rules as Grafana file-provisioned alert rules over postgres_exporter metrics |
| `alarm-channels.md` | Human-visible versus agent-visible channels, and how to route on the `audience` tag |
| `tools/aggregate_metrics.py` | Buckets a long-format metrics CSV and back-tests a proposed threshold. Standard library only |
| `tests/` | `python3 -m pytest 02-alarms/tests` |

## Guardrails

- Aggregate before reading. No raw log dumps into context: the skill refuses them.
- Read-only tools. Acknowledging or closing a problem, or creating a maintenance window, counts as a write.
- The output is a draft MR. Triggers are applied by your normal pipeline after a human review, never by the agent through an API.

## Try it without a live stack

```bash
python3 02-alarms/tools/aggregate_metrics.py sample-data/metrics-db-sessions.csv --bucket 1d --summary-only --baseline-buckets 1
python3 02-alarms/tools/aggregate_metrics.py sample-data/metrics-db-sessions.csv --backtest 'pgsql.connections.idle_in_transaction>20' --for 30m
```

Then, in Claude Code: `/preventative-alarms sample-data/incident-brief.md using sample-data/ as the data source. Do not read sample-data/answer-key/.`
