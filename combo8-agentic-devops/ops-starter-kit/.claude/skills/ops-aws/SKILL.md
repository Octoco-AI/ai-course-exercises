---
name: ops-aws
description: Investigate AWS read-only — CloudWatch alarms and alarm history, metric statistics, Logs Insights aggregations, and describe/list calls on ECS, EKS, RDS and ALB — through the AWS Labs CloudWatch MCP server or the aws CLI as a view-only role. Use when the user asks why an AWS alarm fired, what a metric did around an incident, which errors spiked in CloudWatch Logs, or what changed in an AWS service.
allowed-tools: mcp__cloudwatch__get_active_alarms mcp__cloudwatch__get_alarm_history mcp__cloudwatch__get_metric_data mcp__cloudwatch__get_metric_metadata mcp__cloudwatch__analyze_metric mcp__cloudwatch__get_recommended_metric_alarms mcp__cloudwatch__describe_log_groups mcp__cloudwatch__analyze_log_group mcp__cloudwatch__execute_log_insights_query mcp__cloudwatch__get_logs_insight_query_results Bash(aws sts get-caller-identity*) Bash(aws cloudwatch describe-*) Bash(aws cloudwatch get-metric-*) Bash(aws logs start-query *) Bash(aws logs get-query-results *) Bash(aws logs describe-log-groups *) Bash(aws ecs describe-*) Bash(aws ecs list-*) Bash(aws rds describe-*) Bash(aws elbv2 describe-*) Bash(aws eks describe-*) Bash(aws cloudtrail lookup-events *)
---

# AWS, read-only

You act as the `ops-reader` role: `ViewOnlyAccess` plus the CloudWatch metric,
alarm and Logs Insights reads in `01-access/token-checklist.md`. You cannot change,
restart, scale, deploy or delete anything, read secrets, or read S3 objects. The
CloudWatch MCP server only reads, and the hook blocks mutating `aws` operations.
If you are blocked, that is the design working.

<!-- VERIFY: tool names against the awslabs.cloudwatch-mcp-server version you pin
     (`/mcp` lists them). The template keys the server as `cloudwatch`. -->

## Before the first query

1. Run `aws sts get-caller-identity` (or check the profile the MCP server uses) and
   say which **account and role** you are on. If it is not a read-only role, or not
   the account the user meant, stop.
2. Confirm the **region** and the **time window** in UTC: the incident ± 30
   minutes unless told otherwise. Every query carries explicit start and end times.
3. Name the **resource**: the service, cluster, DB instance, load balancer or
   function. Never sweep every region or every log group.

## Query well

- **Alarms first.** `get_active_alarms`, then `get_alarm_history` for the alarm
  that fired: when did it go `ALARM`, how often has it flapped in 14 days?
- **Metrics as statistics, never raw datapoints.** `get_metric_data` or
  `aws cloudwatch get-metric-statistics` with a period that keeps the result under
  ~200 points (1 h period for 7 days, 5 min for 6 hours). Ask for `Maximum` and
  `Average`, plus `p99` for latency. `analyze_metric` gives trend and seasonality.
- **Logs as Logs Insights aggregations.** Start with counts, not lines — the
  shapes in `02-alarms/prompts/cloudwatch-logs-insights.md`:

  ```text
  fields @timestamp, @message
  | filter @message like /(?i)(error|exception|timeout)/
  | stats count(*) as errors by bin(5m)
  ```

  then `stats count(*) by <error field>` with `sort ... desc | limit 15`. Read at
  most five sample lines for one specific error, with `fields` limited to what you
  need.
- **What changed.** ECS: `describe-services` → `deployments[]` and `events[]` (the
  last 10); task definition revision and image tag. RDS: `describe-events
  --source-type db-instance --duration <MINUTES>`. Anything else:
  `cloudtrail lookup-events --lookup-attributes AttributeKey=ResourceName,AttributeValue=<NAME>`
  over the window, summarised as who, what API call, when.
- **Limits multiplied out.** For databases: `DatabaseConnections` max against the
  instance's `max_connections` (parameter group) and tasks × pool size per task.

## Never

- Never run a create, update, put, delete, modify, start, stop, reboot, invoke or
  `set-alarm-state` operation — and never ask for the hook to be relaxed.
- Never read secrets or credentials (`get-secret-value`, `--with-decryption`,
  `get-login-password`, session tokens), and never print environment variables of
  a task definition or Lambda function, which often hold them.
- Never pull a log group's raw events in bulk, and never query without a time
  range. `aws logs tail` only with `--since` and a filter, for a quoted excerpt.
- Never assume a role other than the one you were started with.

## Hand back

A triage note: account, region, resource; what is unhealthy and since when; the
evidence (alarm history, metric statistics with period and statistic, the Logs
Insights query and its top rows, recent deployments or events); the most likely
cause and how sure you are; and the recommended change as an MR to the IaC that
owns the resource — "raise the ECS service's `desiredCount` ceiling in
`infra/orders-api.tf`", not "I updated the service".
