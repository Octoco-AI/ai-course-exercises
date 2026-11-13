# Prompt — CloudWatch metrics and Logs Insights aggregations, never raw events

Use with the read-only `cloudwatch` MCP server or the `aws` CLI as the `ops-reader` role (see `01-access/`). The role should read metrics, alarms and the log groups named below, nothing else. Replace every `<PLACEHOLDER>`.

---

I am investigating **<INCIDENT_OR_ALARM_CLASS>** for **<SERVICE_NAME>** in account **<ACCOUNT_ID>**, region **<REGION>**. Impact began at **<IMPACT_START_UTC>**. Logs are in **<LOG_GROUPS, e.g. /ecs/orders-api>**. The database is **<DB_INSTANCE_ID>**, behind **<LOAD_BALANCER>**.

Rules for every query in this session:

- Every metric call and every Logs Insights query has an explicit start and end time.
- Metrics come back as statistics with a period that keeps each series under 200 points. Never raw datapoints at 1-minute resolution over days.
- Every Logs Insights query ends in `stats`. No query returns raw events, except the one in step 5, after you ask me.
- Never print environment variables, secrets, request bodies or user identifiers.

Steps:

1. **What alarmed, and when.** `get_active_alarms`, then `get_alarm_history` for the alarm that fired, over 14 days. Did it flap before? What is its threshold, period and evaluation count?

2. **Shape of the window, as metrics.** For <LOOKBACK, default 7 days> before impact, period 1 h, statistics `Maximum` and `Average`:

   | Namespace | Metric | Dimension |
   |---|---|---|
   | `AWS/RDS` | `DatabaseConnections`, `CPUUtilization`, `FreeableMemory`, `ReadLatency` | `DBInstanceIdentifier=<DB_INSTANCE_ID>` |
   | `AWS/ApplicationELB` | `HTTPCode_Target_5XX_Count` (Sum), `TargetResponseTime` (p99) | `LoadBalancer=<LB_DIMENSION>` |
   | `AWS/ECS` | `CPUUtilization`, `MemoryUtilization` | `ClusterName`, `ServiceName` |
   | `ECS/ContainerInsights` | `RunningTaskCount` | `ClusterName`, `ServiceName` |

   Use `analyze_metric` for trend and seasonality on the one that looks like it is climbing. Report the slope per day, not the chart.

3. **Errors per hour, from logs.**

   ```text
   fields @timestamp, @message
   | filter @message like /(?i)(error|exception|timeout|refused)/
   | stats count(*) as errors by bin(1h)
   | sort bin(1h) asc
   ```

4. **What kinds of error.** For the six hours around impact. If the logs are JSON, group by the real fields (`level`, `error.type`, `logger`); otherwise by a normalised message prefix:

   ```text
   fields @timestamp, @message
   | filter @message like /(?i)(error|exception)/
   | parse @message /(?<err>[A-Za-z]+(Exception|Error))/
   | stats count(*) as n, earliest(@timestamp) as first_seen by err
   | sort n desc
   | limit 15
   ```

   `analyze_log_group` gives the same answer as patterns and anomalies, with no query to write. Use it first if the log group is large.

5. **One example.** Only for the top error type, and only if I agree: `fields @timestamp, @message | filter @message like /<ERR>/ | limit 3`.

6. **Database sessions, if the database is involved.** `DatabaseConnections` Maximum against `max_connections` for the instance's parameter group (`aws rds describe-db-parameters --db-parameter-group-name <GROUP> --query "Parameters[?ParameterName=='max_connections']"`), and ECS running tasks × pool size per task. Point-in-time session detail (who holds them, idle in transaction) is a human query: `db-stats.md`.

Hand back: a table of signal, normal range, first left normal, lead time before impact, and whether an alarm existed for it. Then the exact queries you ran, so I can rerun them in the console.
