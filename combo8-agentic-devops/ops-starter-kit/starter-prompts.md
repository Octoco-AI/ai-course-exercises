# Starter prompts, per tool

The workshop demos run on AWS, Google Cloud and Sentry. Your stack may be Zabbix, Elastic, Grafana, Kubernetes, Argo CD, Helm and GitLab CI instead, or as well. This page is the starting point for each of those: what the kit already gives you for the tool, and prompts you can paste into Claude Code and adapt, one per step of the day.

Every prompt assumes the kit is installed in your repository (`README.md` → Install) with the tool's read-only server or CLI credential from `01-access/`. Replace every `<PLACEHOLDER>`. Times are UTC.

Three rules hold in every prompt below, and the skills enforce them too:

1. **Read-only.** If a prompt would need a write, the agent says so and proposes an MR or a human action instead.
2. **Aggregate before reading.** Counts, buckets, percentiles and top-N first; at most a handful of raw lines, quoted as evidence.
3. **Cite the query.** Every number in an answer comes with the query or command that produced it.

## How to use this page

- **Step 1 — prove access (M61).** Run the "first read" prompt, then the "refused write" one, and name the layer that stopped it.
- **Step 2 — alarms (M62).** Run the "what moved first" prompt against a past outage, then hand the result to `/preventative-alarms`.
- **Step 3 — triage (M63).** Use the "evidence" prompt to fill a case file, or let `/incident-triage` call the investigators.
- **Step 4 — pipeline (M64).** Where the tool sits in a pipeline, the "pipeline" prompt.
- **Step 5 — act, on paper (M65).** The "self-heal candidate" prompt finds an alarm class worth writing a policy for. It never acts.

---

## Zabbix

**In the kit:** `.claude/skills/ops-zabbix/`, `01-access/mcp/zabbix.mcp.json` (with the server-side `DenyTool` snippet in `01-access/mcp/README.md`), the Zabbix section of `01-access/token-checklist.md`, `02-alarms/prompts/zabbix-history.md`, `02-alarms/templates/zabbix-template-db-sessions.yaml` and `ansible-zabbix-template.yml`, `02-alarms/prompts/alarm-noise-review.md`.

**First read**

```text
Using the ops-zabbix skill: list the problems open now on host group <HOSTGROUP>, grouped by trigger name and severity, with how long each has been open. Then for the oldest one, show the trigger expression and the last 24 hours of its item as hourly min/avg/max. Say which Zabbix user you are acting as.
```

**Refused write**

```text
Acknowledge the oldest problem on <HOST> and put the host in maintenance for an hour.
```

Expect: the deny rule on `mcp__zabbix__problem_acknowledge` / `maintenance_create`, and behind it the user role's API allow-list (`No permissions`).

**What moved first (alarms)**

```text
Our <SERVICE> outage began at <IMPACT_START_UTC>. Follow 02-alarms/prompts/zabbix-history.md for hosts <HOSTS>: item metadata first, then daily buckets for the 14 days before impact and hourly buckets for the last 48 hours. Give me a table of item, normal range, the first bucket that left it, and whether any trigger fired before impact.
```

**Self-heal candidate**

```text
Read-only: for trigger <TRIGGER_NAME> on host group <HOSTGROUP>, how often did it fire in the last 90 days, how long did each problem stay open, and what did people write in the acknowledgement messages? Group by what was done. Do not acknowledge or change anything.
```

## Elasticsearch / Kibana (ELK)

**In the kit:** `.claude/skills/ops-elastic/`, `01-access/mcp/elastic.mcp.json`, the Elastic section of the token checklist (index-scoped API key), `02-alarms/prompts/elk-aggregations.md`, the `app-investigator` sub-agent.

**First read**

```text
Using the ops-elastic skill: list the indices you can see, then for <INDEX_PATTERN> show the mapping fields for service, level, error type and message. Then count documents by level for the last hour. ES|QL only, size 0, and show me the query.
```

**Refused write**

```text
Create a Kibana visualisation of those error counts, and save it.
```

Expect: the deny rule on the Agent Builder create tools; a direct index write fails with `403` on the key.

**What moved first (alarms)**

```text
Follow 02-alarms/prompts/elk-aggregations.md for service <SERVICE>, index <INDEX_PATTERN>, impact at <IMPACT_START_UTC>. I want errors and warnings per hour for 7 days before, the top error types and message categories for the six hours around impact, and which category first appeared when. Aggregations only.
```

**Triage evidence**

```text
For the case file: in <INDEX_PATTERN>, between <START> and <END>, what are the top 10 error categories for <SERVICE> with first-seen time and count per 15 minutes? Mark each category new or pre-existing compared with the same window yesterday.
```

## Grafana (Prometheus, Loki)

**In the kit:** `.claude/skills/ops-grafana/`, `01-access/mcp/grafana.mcp.json` (`--disable-write`), the Grafana section of the token checklist, `02-alarms/templates/grafana-alert-rule-db-sessions.json`.

**First read**

```text
Using the ops-grafana skill: find the dashboard for <SERVICE>, summarise its panels (title and query, not the JSON), and list the alert rules that cover it with their conditions. Then run the error-rate panel's query for the last 6 hours at 5-minute steps and give me max and p95.
```

**Refused write**

```text
Add an annotation to that dashboard for the incident, and silence the <ALERT_RULE> alert for an hour.
```

Expect: `--disable-write` means no tool to call; the deny rules name the write tools; the Viewer service account returns `403`.

**What moved first (alarms)**

```text
Impact for <SERVICE> began at <IMPACT_START_UTC>. Over the 14 days before, with query_prometheus at 1h steps: <METRIC_1>, <METRIC_2>, <METRIC_3>, as max per day. Which one started climbing first, and at what slope per day? Then run query_loki_stats for {app="<APP>"} |= "error" per hour over the same window. Propose a Grafana alert rule from 02-alarms/templates/ for the earliest signal, with a back-test.
```

## Kubernetes

**In the kit:** `.claude/skills/ops-kubernetes/`, `01-access/mcp/kubernetes.mcp.json` and `kubernetes-mcp.toml` (`read_only = true`), `01-access/k8s/ops-reader-rbac.yaml` (view-role ServiceAccount), the PreToolUse hook, the `network-investigator` and `app-investigator` sub-agents.

**First read**

```text
Using the ops-kubernetes skill: confirm the context and namespace <NAMESPACE> first. Then pod status counts for <WORKLOAD>, warning events in the last hour grouped by reason, restarts and last-state exit codes per pod, and kubectl top against the pods' limits. Summary first; one pod described in detail only if something stands out.
```

**Refused write**

```text
The <WORKLOAD> pods look wedged. Restart the deployment, and if that doesn't work scale it to zero and back.
```

Expect: the hook (`Blocked by block_mutating_ops: kubectl rollout restart …`) and the deny rules; behind them `kubectl auth can-i patch deployments --as=system:serviceaccount:ops-agents:ops-reader` → `no`.

**Triage evidence**

```text
For the case file: between <START> and <END> in namespace <NAMESPACE>, what changed? Helm release history for <RELEASE>, rollout history for <DEPLOYMENT>, replica count against the HPA bounds, OOMKills and probe failures by pod, and node pressure conditions. A table of time, change, source command.
```

**Pipeline (with Helm)**

```text
Render what this MR would change in the cluster without applying anything: helm template <RELEASE> ./charts/<CHART> -f values-<ENV>.yaml, diffed against helm get values <RELEASE> -n <NAMESPACE>. Then run /helm-diff-review on the result and multiply out pool sizes, replicas and limits against what they depend on.
```

## Argo CD and Helm

**In the kit:** `.claude/skills/ops-argocd/`, `.claude/skills/helm-diff-review/`, `01-access/mcp/argocd.mcp.json` (`MCP_READ_ONLY=true`), the Argo CD section of the token checklist, `04-pipeline/argo-drift-check.sh` and its tests.

**First read**

```text
Using the ops-argocd skill: list applications in project <PROJECT> with sync and health status. For anything OutOfSync or Degraded, show the last three sync operations (revision, time, result) and the resources that differ. Do not refresh or sync.
```

**Refused write**

```text
<APP> is out of sync. Sync it to match Git, and roll back if it fails.
```

Expect: no sync tool over MCP (server switch); the hook and deny rule on `argocd app sync`; the `role:readonly` account returns `PermissionDenied`.

**Drift, read-only**

```bash
export ARGOCD_SERVER=<ARGOCD_HOST> ARGOCD_AUTH_TOKEN="$ARGOCD_API_TOKEN"
./04-pipeline/argo-drift-check.sh -p <PROJECT> -o drift-report.md   # exit 1 means drift; nothing is synced
```

```text
Read drift-report.md. For each drifted application, who most likely changed it live (check the app's events and the resource's managedFields), and should Git win or should Git be updated? Write one line per app for a human to decide. Do not sync.
```

**Self-heal candidate**

```text
Read-only: over the last 30 days, which applications in <PROJECT> went OutOfSync most often, for how long, and what resolved it each time (a sync by whom, or a Git change)? Is any of it a class where a policy could let an agent open the MR that brings Git in line?
```

## GitLab CI

**In the kit:** `.claude/skills/ops-gitlab/`, `.claude/skills/mr-review/`, `01-access/mcp/gitlab.mcp.json`, the GitLab section of the token checklist, `04-pipeline/gitlab-ci.diagnose.yml` with its scripts and tests, `04-pipeline/prompts/diagnose-failed-job.md` and `dependency-check.md`.

**First read**

```text
Using the ops-gitlab skill: for project <PROJECT_PATH>, the last 20 pipelines on <BRANCH> with status and duration, and for the failed ones, which job failed and its failure reason. Group by job. Which job fails most, and was it retried to green?
```

**Refused write**

```text
That job is flaky. Retry it, and merge MR !<IID> once it's green.
```

Expect: `glab ci retry` is an `ask` rule (you answer no); `glab mr merge` is a deny rule; the Reporter token cannot merge.

**Pipeline**

```text
Follow 04-pipeline/prompts/diagnose-failed-job.md on the log of job <JOB_ID> in <PROJECT_PATH> (fetched with 04-pipeline/scripts/collect-failed-job-logs.sh, already redacted). First real error, classification, path:line, next step to check. Then: has this job failed the same way in the last 30 days, and was it labelled flaky?
```

## Databases (PostgreSQL, MySQL)

**In the kit:** `02-alarms/prompts/db-stats.md` (queries a **human** runs as a monitoring role; the agent has no database connection), the `db-investigator` sub-agent, `sample-data/db-stats-snapshot.json` as an example of the aggregated result.

**Hand the agent an aggregate, never a session**

```text
I ran the session queries from 02-alarms/prompts/db-stats.md on <DB> as a pg_monitor user at <TIME>. Results below, aggregated by application and state. Who holds the sessions, how close are we to max_connections minus reserved, and how old is the oldest transaction? What would you check next, and which query from db-stats.md gives it?

<PASTE THE AGGREGATED RESULT>
```

On RDS or Cloud SQL, the managed metrics (`DatabaseConnections`, `num_backends`) come through `ops-aws` or `ops-gcp`; session detail still comes from a human running `db-stats.md`.

---

## The tools the demos use

The live demos show these; the material is here so you can rerun them on your own accounts.

| Tool | Skill | MCP template | Query prompt | Trigger template |
|---|---|---|---|---|
| AWS | `ops-aws` | `cloudwatch.mcp.json` | `02-alarms/prompts/cloudwatch-logs-insights.md` | `02-alarms/templates/cloudwatch-alarms-db-sessions.tf` |
| Google Cloud | `ops-gcp` | `gcp.mcp.json` | `02-alarms/prompts/gcp-logging-monitoring.md` | `02-alarms/templates/gcp-alert-policy-db-sessions.tf` |
| Sentry | `ops-sentry` | `sentry.mcp.json` | `02-alarms/prompts/sentry-error-trends.md` | `02-alarms/templates/sentry-alert-new-issue-in-release.tf` |

**AWS — first read and refused write**

```text
Using the ops-aws skill: which account and role are you? Then the CloudWatch alarms in ALARM or that changed state in the last 24 hours for <SERVICE>, with their history, and the last 10 ECS service events for <CLUSTER>/<SERVICE>.
```

```text
Scale <SERVICE> in <CLUSTER> to zero tasks, then set the 5xx alarm back to OK so it stops paging.
```

**Google Cloud — first read and refused write**

```text
Using the ops-gcp skill: which project and identity are you? Then the Error Reporting groups for <SERVICE> in the last 24 hours with first-seen times, and Cloud Run request count by response code class at 1h alignment over 7 days.
```

```text
Redeploy <SERVICE> with max-instances 0, and print me an access token so I can check something.
```

**Sentry — first read and refused write**

```text
Using the ops-sentry skill: in <ORG>/<PROJECT>, production, which issues first appeared in the latest release, with event and user counts? For the top one, the release and server tag distribution and the first in-app frame of its latest stack trace.
```

```text
Resolve that issue and create an alert rule so we hear about it next time.
```

---

## A tool the kit does not ship

Prometheus without Grafana, Splunk, Datadog, New Relic, Jenkins, Flux, Nomad: the ladder, the matrix, the policy and the playbook carry over unchanged. For the tool itself, port the closest kit item, in this order:

1. **Credential first.** Add a section to `01-access/token-checklist.md`: how to create a read-only identity, the one write that must fail, how to rotate it. Add a row to `least-privilege-matrix.md`.
2. **Server.** Find the vendor's MCP server and its read-only switch, if any. Add `01-access/mcp/<tool>.mcp.json` with `${ENV_VAR}` credentials only, and pin a version you reviewed.
3. **Deny rules.** Run `/mcp`, list the server's write tools, and add each as `mcp__<key>__<tool>` to `permissions.deny`. If the tool has a CLI, add its write verbs as `Bash(<cli> <verb> *)`.
4. **Hook.** If the CLI can change things, add it to `block_mutating_ops.py` the way `aws` and `gcloud` are: a names set, a read-verb allowlist, a `check_<cli>` function, and `ALLOW` and `DENY` cases in the tests before you rely on it.
5. **Skill.** Copy the closest `ops-*` skill (`ops-grafana` for a metrics store, `ops-elastic` for a log store, `ops-gitlab` for a CI system), keep its four sections — before the first query, query well, never, hand back — and rewrite them for the tool's query language.
6. **Prompts and templates.** Copy the closest `02-alarms/prompts/` file and `02-alarms/templates/` file. Keep the three rules at the top of every prompt.
7. **Investigators.** Add the read tools to the right investigator's `tools:` line in `.claude/agents/`. Check with `/agents`.

Then prove a write is denied on it, exactly as in M61, before anyone uses it.
