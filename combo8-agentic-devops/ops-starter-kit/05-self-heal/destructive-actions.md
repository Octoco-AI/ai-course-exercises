# Destructive-actions list — ops

Actions that **no agent performs, at any rung of the ladder, without a named human's confirmation**. In this kit's design agents never perform them at all. The list is what the deny rules, the PreToolUse hook and the token scopes in `01-access/` enforce, and what every self-heal policy cites as "never".

Start from this list, delete what does not apply, add what is specific to your stack, and commit it. It follows the categories in the governance module's destructive-actions list (delete, send, publish, spend, access, grant), with the ops-specific ones made explicit.

For each row, fill **who confirms**, **how** (in the MR, in chat, by a second person at the keyboard), and **where it is enforced**. A rule with nothing in the "Enforced by" column is a hope, not a rule.

| Id | Category | Action | Examples | Who confirms | Enforced by |
|---|---|---|---|---|---|
| DA-01 | Delete | Delete or truncate data or files | `rm` on a server, `kubectl delete pvc`, deleting an Elasticsearch index, `DROP` / `TRUNCATE` / unscoped `DELETE`, `aws s3 rm`, `gsutil rm` | <ROLE> | settings deny rules; hook; read-only tokens and view-only cloud roles |
| DA-02 | Delete | Delete workloads or releases | `kubectl delete`, `helm uninstall`, `argocd app delete` | <ROLE> | hook (kubectl, helm, argocd verbs); view-role ServiceAccount; `MCP_READ_ONLY` |
| DA-03 | Disrupt | Restart, evict or reschedule | `kubectl rollout restart`, deleting pods, `cordon` / `drain`, `systemctl restart`, failover, `aws ecs update-service --force-new-deployment`, `aws rds reboot-db-instance`, `gcloud sql instances restart` | <ROLE> | hook; view-role ServiceAccount; view-only cloud roles |
| DA-04 | Disrupt | Scale | `kubectl scale`, editing an HPA, replicas to 0, `aws ecs update-service --desired-count`, `gcloud run services update --max-instances` | <ROLE> | hook; `read_only` on the Kubernetes MCP server; view-only cloud roles |
| DA-05 | Change live | Change running config outside Git | `kubectl apply` / `edit` / `patch` / `set`, `helm upgrade` / `rollback`, `argocd app set` / `patch` | <ROLE> | hook; GitOps (live changes are reverted anyway) |
| DA-06 | Publish | Deploy or sync | `argocd app sync`, `argocd app rollback`, `gcloud run deploy`, `gcloud run services update-traffic`, merging to a protected branch, tagging a release, running a deploy job | <ROLE> | `MCP_READ_ONLY=true`; protected branches; agent tokens lack Maintainer; CI job has no `environment:` |
| DA-07 | Change live | Run configuration management against hosts | `ansible-playbook` without `--check`, Terraform `apply` | <ROLE> | no host credentials in agent context; hook |
| DA-08 | Access | Interactive or privileged access | `ssh`, `kubectl exec`, `kubectl port-forward` to a database, reading Secrets, `aws ssm start-session`, `aws ecs execute-command`, `gcloud compute ssh`, reading cloud secrets or printing access tokens | <ROLE> | hook; Secrets denied in the Kubernetes MCP config; view role excludes Secrets; `ViewOnlyAccess` excludes secret values |
| DA-09 | Hide signal | Acknowledge, close, suppress or silence alarms | Zabbix problem acknowledge, close or suppress; maintenance windows; Grafana silences; `aws cloudwatch set-alarm-state` or `disable-alarm-actions`; resolving or ignoring a Sentry issue | <ROLE> | Zabbix DenyTool for write tools; read-only Zabbix user; Grafana `--disable-write`; hook; Sentry `--skills inspect` and read-scoped token |
| DA-10 | Change monitoring | Create, edit or delete triggers, alert rules or dashboards directly | Zabbix template import, Grafana rule creation through the API, `aws cloudwatch put-metric-alarm`, a Cloud Monitoring policy or Sentry alert rule created outside Terraform | <ROLE> | read-only monitoring tokens; changes go by MR only (`02-alarms/`) |
| DA-11 | Database | Terminate sessions or change settings | `pg_terminate_backend`, `ALTER SYSTEM`, killing queries | <ROLE> | agents have no database connection |
| DA-12 | Grant | Grant or widen any permission | RBAC bindings, new tokens, adding a user to a group, changing CI/CD variables | <ROLE> | agent tokens cannot manage members or variables |
| DA-13 | Spend | Incur non-trivial cost | Scaling node pools, larger instance types, long model runs beyond `<BUDGET>` | <ROLE> | spend limit on the model key; `--max-turns`; job `timeout` |
| DA-14 | Send | Communicate outside the team | Status-page updates, customer or vendor emails, posting outside the team's channels | <ROLE> | no such integrations granted |

## How to use it

- **In settings and hooks.** Each row's command patterns belong in a `deny` rule or the PreToolUse hook (`01-access/`). Add a test case to the hook for every pattern you add.
- **In reviews.** The `mr-review` skill flags any MR that performs or enables one of these as *blocking until a named human confirms*.
- **In self-heal policies.** Every policy lists the rows it relies on *not* taking.
- **In incidents.** If an agent ever performs one of these, that is an incident in its own right. Run the governance kill switch and review the agent inventory entry.
