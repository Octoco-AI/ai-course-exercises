# Trigger proposal as code — CloudWatch alarms for PostgreSQL session exhaustion on RDS.
#
# The same three rules as zabbix-template-db-sessions.yaml and
# grafana-alert-rule-db-sessions.json, for a team whose monitoring lives in AWS.
# The agent drafts this file in an MR; your pipeline runs `terraform plan`, a human
# reviews the plan, and the normal apply path applies it. The agent never applies.
#
# Rule                                   Audience  Back-test on sample-data/
# idle in transaction > 20 for 30m       agent     first fires 2026-10-07 10:30
# idle in transaction > 50 for 2h        human     ticket, 2026-10-11 14:00
# total sessions > 85 % of usable, 10m   human     page,   2026-10-12 12:10
#
# RDS publishes DatabaseConnections but not sessions by state. The idle-in-transaction
# rules need a custom metric: the CloudWatch agent scraping postgres_exporter
# (`pg_stat_activity_count{state="idle in transaction"}`), or a Lambda that runs the
# db-stats.md count query as a monitoring role. VERIFY the namespace, metric name and
# dimensions your exporter publishes before you merge.

variable "db_instance_id" {
  type        = string
  description = "RDS instance identifier, e.g. orders-db"
}

variable "usable_connections" {
  type        = number
  description = "max_connections minus superuser_reserved_connections (300 - 3 = 297 in the sample)"
  default     = 297
}

variable "custom_namespace" {
  type    = string
  default = "<CUSTOM_NAMESPACE>" # e.g. "CWAgent" or "Custom/Postgres"
}

variable "agent_digest_topic_arn" {
  type        = string
  description = "SNS topic read by the agent digest. Never a paging route (02-alarms/alarm-channels.md)."
}

variable "ticket_topic_arn" {
  type = string
}

variable "page_topic_arn" {
  type = string
}

locals {
  common_tags = {
    owner       = "<TEAM>"
    proposed_by = "preventative-alarms"
    incident    = "<INCIDENT_ID>"
  }
}

resource "aws_cloudwatch_metric_alarm" "idle_in_tx_early" {
  alarm_name          = "${var.db_instance_id}-idle-in-transaction-early"
  alarm_description   = "Leading indicator: sessions idle in transaction above 20 for 30 minutes. Agent channel only; must not page."
  namespace           = var.custom_namespace
  metric_name         = "pg_idle_in_transaction" # VERIFY against your exporter
  dimensions          = { DBInstanceIdentifier = var.db_instance_id }
  statistic           = "Minimum" # sustained: every sample in the period is above
  period              = 300
  evaluation_periods  = 6
  datapoints_to_alarm = 6
  threshold           = 20
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "missing"
  alarm_actions       = [var.agent_digest_topic_arn]
  tags                = merge(local.common_tags, { audience = "agent" })
}

resource "aws_cloudwatch_metric_alarm" "idle_in_tx_ticket" {
  alarm_name          = "${var.db_instance_id}-idle-in-transaction-sustained"
  alarm_description   = "Sessions idle in transaction above 50 for 2 hours: a leak, not a spike. Opens a ticket for the owning team."
  namespace           = var.custom_namespace
  metric_name         = "pg_idle_in_transaction"
  dimensions          = { DBInstanceIdentifier = var.db_instance_id }
  statistic           = "Minimum"
  period              = 300
  evaluation_periods  = 24
  datapoints_to_alarm = 24
  threshold           = 50
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "missing"
  alarm_actions       = [var.ticket_topic_arn]
  ok_actions          = [var.ticket_topic_arn]
  tags                = merge(local.common_tags, { audience = "human", severity = "ticket" })
}

resource "aws_cloudwatch_metric_alarm" "sessions_near_limit" {
  alarm_name          = "${var.db_instance_id}-sessions-near-limit"
  alarm_description   = "Total sessions above 85 % of usable connections for 10 minutes. Pages on-call."
  namespace           = "AWS/RDS"
  metric_name         = "DatabaseConnections"
  dimensions          = { DBInstanceIdentifier = var.db_instance_id }
  statistic           = "Minimum"
  period              = 60
  evaluation_periods  = 10
  datapoints_to_alarm = 10
  threshold           = floor(var.usable_connections * 0.85) # 252 for 297
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "breaching" # no data from the database during an incident is not "OK"
  alarm_actions       = [var.page_topic_arn]
  ok_actions          = [var.page_topic_arn]
  tags                = merge(local.common_tags, { audience = "human", severity = "page" })
}
