# Trigger proposal as code — Cloud Monitoring alert policies for PostgreSQL session
# exhaustion on Cloud SQL.
#
# The same three rules as zabbix-template-db-sessions.yaml and
# grafana-alert-rule-db-sessions.json, for a team whose monitoring lives in Google
# Cloud. The agent drafts this file in an MR; your pipeline runs `terraform plan`, a
# human reviews the plan, and the normal apply path applies it. The agent never applies.
#
# Rule                                   Audience  Back-test on sample-data/
# idle in transaction > 20 for 30m       agent     first fires 2026-10-07 10:30
# idle in transaction > 50 for 2h        human     ticket, 2026-10-11 14:00
# total sessions > 85 % of usable, 10m   human     page,   2026-10-12 12:10
#
# VERIFY: Cloud SQL for PostgreSQL publishes
# cloudsql.googleapis.com/database/postgresql/num_backends_by_state with a `state`
# label; check the label value for idle-in-transaction sessions in Metrics Explorer
# before you merge. num_backends is the total.

variable "project_id" {
  type = string
}

variable "instance_id" {
  type        = string
  description = "Cloud SQL instance name, e.g. orders-db"
}

variable "usable_connections" {
  type        = number
  description = "max_connections minus superuser_reserved_connections (300 - 3 = 297 in the sample)"
  default     = 297
}

variable "agent_digest_channel" {
  type        = string
  description = "Notification channel read by the agent digest (a Pub/Sub channel). Never a paging route."
}

variable "ticket_channel" {
  type = string
}

variable "page_channel" {
  type = string
}

locals {
  database_filter = "resource.type = \"cloudsql_database\" AND resource.labels.database_id = \"${var.project_id}:${var.instance_id}\""
  idle_in_tx      = "${local.database_filter} AND metric.type = \"cloudsql.googleapis.com/database/postgresql/num_backends_by_state\" AND metric.labels.state = \"idle_in_transaction\""
  labels = {
    owner       = "<team>"
    proposed_by = "preventative-alarms"
    incident    = "<incident-id>"
  }
}

resource "google_monitoring_alert_policy" "idle_in_tx_early" {
  project      = var.project_id
  display_name = "${var.instance_id}: idle in transaction > 20 for 30m (early)"
  combiner     = "OR"
  severity     = "WARNING"
  user_labels  = merge(local.labels, { audience = "agent" })

  conditions {
    display_name = "idle in transaction above 20"
    condition_threshold {
      filter          = local.idle_in_tx
      comparison      = "COMPARISON_GT"
      threshold_value = 20
      duration        = "1800s"
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_MIN" # sustained: the minimum in each window is above
      }
    }
  }

  documentation {
    content   = "Leading indicator from the preventative-alarms review. Agent channel only; must not page (02-alarms/alarm-channels.md)."
    mime_type = "text/markdown"
  }

  notification_channels = [var.agent_digest_channel]
}

resource "google_monitoring_alert_policy" "idle_in_tx_ticket" {
  project      = var.project_id
  display_name = "${var.instance_id}: idle in transaction > 50 for 2h (ticket)"
  combiner     = "OR"
  severity     = "ERROR"
  user_labels  = merge(local.labels, { audience = "human", route = "ticket" })

  conditions {
    display_name = "idle in transaction above 50"
    condition_threshold {
      filter          = local.idle_in_tx
      comparison      = "COMPARISON_GT"
      threshold_value = 50
      duration        = "7200s"
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_MIN"
      }
    }
  }

  documentation {
    content   = "A leak, not a spike: sessions stuck idle in transaction for two hours. Ticket for the owning team; see the runbook."
    mime_type = "text/markdown"
  }

  notification_channels = [var.ticket_channel]
}

resource "google_monitoring_alert_policy" "sessions_near_limit" {
  project      = var.project_id
  display_name = "${var.instance_id}: sessions > 85% of usable for 10m (page)"
  combiner     = "OR"
  severity     = "CRITICAL"
  user_labels  = merge(local.labels, { audience = "human", route = "page" })

  conditions {
    display_name = "total sessions near the limit"
    condition_threshold {
      filter          = "${local.database_filter} AND metric.type = \"cloudsql.googleapis.com/database/postgresql/num_backends\""
      comparison      = "COMPARISON_GT"
      threshold_value = floor(var.usable_connections * 0.85) # 252 for 297
      duration        = "600s"
      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_MIN"
        cross_series_reducer = "REDUCE_SUM" # one line for the instance, across databases
      }
    }
  }

  documentation {
    content   = "Sessions are about to run out. Pages on-call."
    mime_type = "text/markdown"
  }

  notification_channels = [var.page_channel]
}
