# Trigger proposal as code — Sentry issue alerts for the application side of the
# sample incident (the connection-pool leak warning that stopped at a deploy, and
# the error storm at impact).
#
# Sentry's own alerts are the application-layer counterpart of the database rules in
# the other templates: they fire on what the code reports, not on what the database
# sees. The agent drafts this file in an MR; a human reviews `terraform plan`.
#
# Rule                                                  Audience
# a new issue, level >= warning, in the latest release  agent (digest)
# any issue > 100 events in 1h in production            human (ticket)
#
# Provider: jianyuan/sentry, using the `*_v2` attributes (provider 0.14.2 or later).
# VERIFY: the provider now steers new work to `sentry_alert`; check which resource
# your pinned provider version expects before you merge.

variable "organization" {
  type = string
}

variable "project" {
  type        = string
  description = "Sentry project slug, e.g. orders-api"
}

variable "agent_digest_slack_workspace" {
  type        = string
  description = "Integration id of the Slack workspace; the channel is read by the agent digest, not by on-call."
}

variable "owning_team_id" {
  type        = string
  description = "Internal id of the owning team (data.sentry_team.<x>.internal_id)."
}

resource "sentry_issue_alert" "new_issue_in_latest_release" {
  organization = var.organization
  project      = var.project
  name         = "New warning or error in the latest release (agent digest)"
  environment  = "production"
  action_match = "any"
  filter_match = "all"
  frequency    = 1440 # at most once a day per issue

  conditions_v2 = [
    { first_seen_event = {} },
  ]

  filters_v2 = [
    { latest_release = {} },
    { level = { match = "GREATER_OR_EQUAL", level = "warning" } },
  ]

  actions_v2 = [
    { slack_notify_service = {
      workspace = var.agent_digest_slack_workspace
      channel   = "<#AGENT_DIGEST_CHANNEL>"
      tags      = ["release", "environment", "level"]
    } },
  ]
}

resource "sentry_issue_alert" "error_burst" {
  organization = var.organization
  project      = var.project
  name         = "Issue above 100 events in an hour (ticket)"
  environment  = "production"
  action_match = "any"
  filter_match = "all"
  frequency    = 60

  conditions_v2 = [
    { event_frequency = { comparison_type = "count", value = 100, interval = "1h" } },
  ]

  filters_v2 = [
    { level = { match = "GREATER_OR_EQUAL", level = "error" } },
  ]

  actions_v2 = [
    { notify_email = { target_type = "Team", target_identifier = var.owning_team_id, fallthrough_type = "ActiveMembers" } },
  ]
}
