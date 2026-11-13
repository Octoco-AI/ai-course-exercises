# Prompt — Google Cloud Monitoring and Logging aggregations, never raw entries

Use with the read-only `gcp` MCP server or `gcloud` as the `ops-reader` service account, by impersonation (see `01-access/`). Replace every `<PLACEHOLDER>`.

---

I am investigating **<INCIDENT_OR_ALARM_CLASS>** for **<SERVICE_NAME>** in project **<PROJECT_ID>**, region **<REGION>**. Impact began at **<IMPACT_START_UTC>**. The service runs on **<Cloud Run | GKE | Compute Engine>**; the database is Cloud SQL instance **<INSTANCE_ID>**.

Rules for every query in this session:

- Every time-series call has an interval, an aligner and an alignment period that keeps each series under 200 points.
- Every log filter has `timestamp>="<START>"` and `timestamp<"<END>"` and a `resource.type`. `pageSize` no more than 20, and only after step 4 tells you which error to look at.
- Logging has no server-side aggregation through this server. Count by narrowing the filter, or read an existing log-based metric as a time series. Do not pull pages of entries to count them yourself.
- Never print `httpRequest.remoteIp`, user fields, request bodies or tokens.

Steps:

1. **What alerted, and what it checks.** `list_alert_policies`: the condition of the policy that fired, its duration and its threshold. Note what it does not check.

2. **Shape of the window, as metrics.** For <LOOKBACK, default 7 days> before impact, alignment period 1 h:

   | Metric type | Aligner / reducer | Filter |
   |---|---|---|
   | `run.googleapis.com/request_count` | `ALIGN_RATE`, reduce `REDUCE_SUM` by `metric.label.response_code_class` | `resource.label.service_name="<SERVICE_NAME>"` |
   | `run.googleapis.com/request_latencies` | `ALIGN_PERCENTILE_99` | same |
   | `run.googleapis.com/container/instance_count` | `ALIGN_MAX` | same |
   | `cloudsql.googleapis.com/database/postgresql/num_backends` | `ALIGN_MAX` | `resource.label.database_id="<PROJECT_ID>:<INSTANCE_ID>"` |
   | `cloudsql.googleapis.com/database/cpu/utilization` | `ALIGN_MAX` | same |
   | `kubernetes.io/container/restart_count` (GKE) | `ALIGN_DELTA`, reduce `REDUCE_SUM` | `resource.label.namespace_name="<NAMESPACE>"` |

   Report the slope per day of whatever is climbing, not the chart.

3. **New errors.** `list_group_stats` for the window: error groups with counts, affected services and first-seen time. Mark each new or pre-existing.

4. **Errors per class, from logs.** For each of the top three error groups, count entries in the six hours around impact with a narrow filter:

   ```text
   resource.type="cloud_run_revision"
   resource.labels.service_name="<SERVICE_NAME>"
   severity>=ERROR
   textPayload:"<ERROR_CLASS>" OR jsonPayload.message:"<ERROR_CLASS>"
   timestamp>="<START>" timestamp<"<END>"
   ```

   If a log-based metric already exists for errors (`logging.googleapis.com/user/<METRIC>`), read that with `list_time_series` instead: it is the aggregation you want.

5. **One example.** Only for the top error group, and only if I agree: `pageSize: 3`, `orderBy: "timestamp desc"`.

6. **What changed.** Revisions of the service in the window (`gcloud run revisions list --service <SERVICE_NAME> --region <REGION> --format "table(metadata.name,metadata.creationTimestamp,spec.containers[0].image)"`), and the Admin Activity audit log for the service and the Cloud SQL instance, as who, which method, when.

7. **Database sessions, if the database is involved.** `num_backends` max against the instance's `max_connections` flag (`gcloud sql instances describe <INSTANCE_ID> --format "value(settings.databaseFlags)"`; absent means the tier default), and max instances × pool size per instance. Session detail is a human query: `db-stats.md`.

Hand back: a table of signal, normal range, first left normal, lead time before impact, and whether an alert policy covered it. Then the exact filters and time-series parameters, so I can rerun them in Metrics Explorer and Logs Explorer.
