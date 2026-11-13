# Read-only credential checklist

For each system: **create** the read-only credential, **prove** a write is denied
*before* an agent ever holds it, and know how to **rotate** it. A human does every
step on this page. None of it is a task for the agent.

Replace every `<PLACEHOLDER>`. Hosts below are examples (`*.example.internal`).
Keep tokens out of shell history: read them into a variable with `read -s`, or
pipe them straight into your secrets manager.

**Universal rules**

- [ ] One credential per person (interactive) or per agent (unattended). Never shared.
- [ ] Every credential has an expiry. "Never expires" is a finding.
- [ ] The scope is written in `least-privilege-matrix.md` before the token exists.
- [ ] The write test below was run and **failed** — paste the error into the matrix row's review notes.
- [ ] The token lives in a secrets manager or masked CI variable, reaches Claude Code as an environment variable, and appears in no file in any repo.

---

## Zabbix — read-only user and API token

**Create**

- [ ] *Users → User roles*: create role `agent-readonly`, user type **User**.
  Under *API*, enable access and choose **Allow list** with only read methods.
  Zabbix supports wildcards such as `dashboard.*` and `*.export`; `*.get` follows
  the same pattern (VERIFY: confirm `*.get` matches every `get` method on your
  version, or list `host.get`, `problem.get`, `trigger.get`, `item.get`,
  `history.get`, `trend.get`, `event.get`, `hostgroup.get` explicitly).
  Untick every UI action that changes state.
- [ ] *Users → User groups*: create group `agents-readonly` with **Read** permission
  on host groups `<HOSTGROUPS>` only.
- [ ] Create the user (per engineer: their own user; unattended: `svc-<agent-name>`)
  in that group with that role.
- [ ] *Users → API tokens*: create a token for that user with an expiry of
  `<30_DAYS>`. Copy it once into the secrets manager → `ZABBIX_API_TOKEN`.

**Prove the write is denied**

```bash
ZBX=https://zabbix.example.internal/api_jsonrpc.php
# Read works:
curl -s "$ZBX" -H "Content-Type: application/json-rpc" -H "Authorization: Bearer $ZABBIX_API_TOKEN" \
  -d '{"jsonrpc":"2.0","method":"host.get","params":{"output":["host"],"limit":1},"id":1}'
# Write must fail with a "No permissions" error:
curl -s "$ZBX" -H "Content-Type: application/json-rpc" -H "Authorization: Bearer $ZABBIX_API_TOKEN" \
  -d '{"jsonrpc":"2.0","method":"maintenance.create","params":{"name":"agent-write-test","active_since":0,"active_till":1,"groups":[{"groupid":"<ANY_GROUPID>"}],"timeperiods":[{"period":3600}]},"id":2}'
```

(Zabbix older than 6.4 takes the token in an `"auth"` field rather than the
`Authorization` header.)

**Rotate**: create a new token, update the secret, confirm the agent still reads,
then delete the old token in *Users → API tokens*. Expired tokens stop working on
their own; set a calendar reminder `<7_DAYS>` before expiry.

---

## Elasticsearch / Kibana — index-scoped API key

**Create** (in Kibana *Dev Tools*, as a user who already has at least these rights):

```json
POST /_security/api_key
{
  "name": "agent-readonly-<NAME>",
  "expiration": "30d",
  "role_descriptors": {
    "agent-readonly": {
      "cluster": ["monitor_inference"],
      "indices": [
        {
          "names": ["<INDEX_PATTERN_1>", "<INDEX_PATTERN_2>"],
          "privileges": ["read", "view_index_metadata"]
        }
      ],
      "applications": [
        {
          "application": "kibana-.kibana",
          "privileges": ["feature_agentBuilder.read"],
          "resources": ["space:<SPACE_ID>"]
        }
      ]
    }
  }
}
```

- [ ] `names` lists the specific patterns the agent needs (`logs-app-*`), never `*`.
- [ ] No `write`, `index`, `delete`, `manage` or `all` privilege anywhere.
- [ ] Copy the `encoded` value from the response → `ELASTIC_MCP_API_KEY`.

Elastic's own example also grants `feature_actions.read`; leave it out unless you
need the agent to see connectors. An API key can never exceed the rights of the
user who created it, so create it as a user who is not a superuser.

**Prove the write is denied**

```bash
ES=https://elasticsearch.example.internal:9200
curl -s "$ES/_security/_authenticate" -H "Authorization: ApiKey $ELASTIC_MCP_API_KEY"         # shows the key
curl -s -XPOST "$ES/<AN_ALLOWED_INDEX>/_doc" -H "Authorization: ApiKey $ELASTIC_MCP_API_KEY" \
  -H "Content-Type: application/json" -d '{"agent":"write-test"}'                             # must be 403
curl -s "$ES/<AN_INDEX_NOT_IN_THE_LIST>/_search?size=0" -H "Authorization: ApiKey $ELASTIC_MCP_API_KEY"  # must be 403
```

**Rotate**: create a new key, swap the secret, then
`DELETE /_security/api_key {"ids": ["<OLD_KEY_ID>"]}`. Keys created with
`expiration` stop working on their own.

---

## Argo CD — read-only local account

**Create**

- [ ] In `argocd-cm`: `accounts.ops-reader: apiKey` (API tokens only, no UI login).
- [ ] In `argocd-rbac-cm` `policy.csv`, either bind the built-in role:

  ```csv
  g, ops-reader, role:readonly
  ```

  or, to limit the account to some projects, define a narrower role:

  ```csv
  p, role:ops-reader, applications, get, <PROJECT>/*, allow
  p, role:ops-reader, logs, get, <PROJECT>/*, allow
  p, role:ops-reader, projects, get, <PROJECT>, allow
  g, ops-reader, role:ops-reader
  ```

  The built-in `role:readonly` grants `get` on applications, application sets,
  clusters, repositories, projects, accounts, certificates, GPG keys and logs in
  every project. Nothing in it can sync, set or delete.
- [ ] Generate the token **with an expiry** (without `--expires-in` it never expires):

  ```bash
  argocd account generate-token --account ops-reader --expires-in 720h
  ```

  → `ARGOCD_API_TOKEN`, the name the argocd-mcp server reads. The `argocd` CLI reads
  the same token as `ARGOCD_AUTH_TOKEN`; `04-pipeline/argo-drift-check.sh` falls back
  from one to the other, so set it once.

**Prove the write is denied**

```bash
argocd account can-i sync applications '<PROJECT>/*' --auth-token "$ARGOCD_API_TOKEN" --server argocd.example.internal   # must print "no"
argocd app sync <APP> --auth-token "$ARGOCD_API_TOKEN" --server argocd.example.internal                                     # must be PermissionDenied
```

**Rotate**: generate a new token, swap the secret, then remove the old one with
`argocd account delete-token --account ops-reader <TOKEN_ID>` (list ids with
`argocd account get --account ops-reader`).

---

## Kubernetes — view-role ServiceAccount

**Create**

- [ ] Review and apply `k8s/ops-reader-rbac.yaml` (ServiceAccount `ops-agents/ops-reader`,
  bound to the built-in `view` ClusterRole plus a small cluster-scoped read role).
- [ ] Mint a short-lived bound token and build a kubeconfig that holds only it:

  ```bash
  TOKEN=$(kubectl create token ops-reader -n ops-agents --duration=8h)
  SERVER=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
  kubectl config view --minify --raw -o jsonpath='{.clusters[0].cluster.certificate-authority-data}' | base64 -d > /tmp/ca.crt
  export KUBECONFIG=$HOME/.kube/ops-reader-<CLUSTER>.kubeconfig
  kubectl config set-cluster <CLUSTER> --server="$SERVER" --certificate-authority=/tmp/ca.crt --embed-certs=true
  kubectl config set-credentials ops-reader --token="$TOKEN"
  kubectl config set-context ops-reader@<CLUSTER> --cluster=<CLUSTER> --user=ops-reader --namespace=<DEFAULT_NAMESPACE>
  kubectl config use-context ops-reader@<CLUSTER>
  rm /tmp/ca.crt; unset TOKEN KUBECONFIG
  ```

  → `OPS_READER_KUBECONFIG=$HOME/.kube/ops-reader-<CLUSTER>.kubeconfig`. The
  API server may cap `--duration` (`--service-account-max-token-expiration`).

**Prove the write is denied**

```bash
SA=system:serviceaccount:ops-agents:ops-reader
kubectl auth can-i --list --as=$SA -n <NAMESPACE>        # only get/list/watch verbs
kubectl auth can-i delete pods --as=$SA -n <NAMESPACE>   # no
kubectl auth can-i create pods/exec --as=$SA -n <NAMESPACE>   # no
kubectl auth can-i get secrets --as=$SA -n <NAMESPACE>   # no
KUBECONFIG=$OPS_READER_KUBECONFIG kubectl -n <NAMESPACE> delete pod <ANY_POD> --dry-run=server   # must be Forbidden
```

**Rotate**: bound tokens expire on their own — mint a new one each working day
(or each CI job). To revoke everything at once, delete and recreate the
ServiceAccount; every token issued to it stops working.

---

## Grafana — Viewer service account

**Create**

- [ ] *Administration → Users and access → Service accounts*: create `ops-reader`
  with role **Viewer**. Restrict folder permissions if some folders are sensitive.
- [ ] Add a token with an expiry of `<30_DAYS>` → `GRAFANA_SERVICE_ACCOUNT_TOKEN`.
- [ ] Start `mcp-grafana` with `--disable-write` (already in `mcp/grafana.mcp.json`).

**Prove the write is denied**

```bash
G=https://grafana.example.internal
curl -s "$G/api/search?limit=1" -H "Authorization: Bearer $GRAFANA_SERVICE_ACCOUNT_TOKEN"     # works
curl -s -XPOST "$G/api/folders" -H "Authorization: Bearer $GRAFANA_SERVICE_ACCOUNT_TOKEN" \
  -H "Content-Type: application/json" -d '{"title":"agent-write-test"}'                        # must be 403
```

**Rotate**: add a new token to the same service account, swap the secret, delete
the old token in the UI or with `DELETE /api/serviceaccounts/<SA_ID>/tokens/<TOKEN_ID>`.

---

## GitLab (self-managed) — read-only by role

GitLab's MCP server accepts an OAuth token with the `mcp` scope or a fine-grained
personal access token; it rejects legacy personal, project and group access tokens.
Each MCP tool still checks the caller's project role. So the **role** is the control.

**Create — interactive (rung 1)**

- [ ] Each engineer signs in through `/mcp` in Claude Code (OAuth). Their own role
  applies, which usually includes push: the deny rules in
  `settings/settings.example.json` are the control for this case. Record that in
  the matrix.

**Create — unattended (rung 1)**

- [ ] A dedicated user `svc-<agent-name>` (or a GitLab service account) with the
  **Reporter** role on `<PROJECTS>` only. Reporter can read code, MRs and pipelines
  and cannot push.
- [ ] For `glab` or API calls: a personal access token for that user with scope
  `read_api` only and an expiry ≤ `<30_DAYS>`. For the MCP server: a fine-grained
  token with the MCP tool resource and Execute permission (VERIFY: what else a
  fine-grained token can be limited to on your version).

**Rung 2 additions**: role **Developer** so it can push branches and open MRs, plus,
on every target project: default branch **protected** (no one may push; merge
allowed for Maintainers), **approval rule** requiring at least one human
approver, and "prevent approval by author" switched on.

**Prove the write is denied** (Reporter token):

```bash
GL=https://gitlab.example.internal/api/v4
curl -s -H "PRIVATE-TOKEN: $GITLAB_READ_TOKEN" "$GL/projects/<PROJECT_ID>/merge_requests?state=opened&per_page=1"   # works
curl -s -XPOST -H "PRIVATE-TOKEN: $GITLAB_READ_TOKEN" \
  "$GL/projects/<PROJECT_ID>/repository/branches?branch=agent-write-test&ref=<DEFAULT_BRANCH>"                     # must be 403
```

On rung 2, prove the gate instead: push a test branch, open an MR, and confirm the
agent's identity **cannot** merge it or approve it.

**Rotate**: `POST /personal_access_tokens/<TOKEN_ID>/rotate` issues a replacement
and revokes the old one; or create a new token, swap, and revoke the old one in
*User settings → Access tokens*. OAuth sessions are revoked under *User settings →
Applications*.

---

## AWS — read-only role through IAM Identity Center or an assumed role

AWS has hundreds of services and no single "read-only" switch on the client. The
role's IAM policy is the whole boundary; `READ_OPERATIONS_ONLY`, the deny rules
and the hook only catch mistakes early.

**Create**

- [ ] A permission set (IAM Identity Center) or IAM role `ops-reader` in
  `<ACCOUNTS>`, with:
  - AWS managed policy **`ViewOnlyAccess`** — lists and describes resources
    without reading data (no `s3:GetObject`, no `secretsmanager:GetSecretValue`);
  - an inline policy for the analysis calls `ViewOnlyAccess` leaves out, scoped to
    the log groups you name:

    ```json
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Sid": "MetricsAndAlarms",
          "Effect": "Allow",
          "Action": ["cloudwatch:GetMetricData", "cloudwatch:GetMetricStatistics", "cloudwatch:ListMetrics",
                     "cloudwatch:DescribeAlarms", "cloudwatch:DescribeAlarmHistory"],
          "Resource": "*"
        },
        {
          "Sid": "LogsInsightsOnNamedGroups",
          "Effect": "Allow",
          "Action": ["logs:StartQuery", "logs:GetQueryResults", "logs:StopQuery", "logs:DescribeLogGroups",
                     "logs:DescribeQueryDefinitions", "logs:ListLogAnomalyDetectors", "logs:ListAnomalies",
                     "logs:FilterLogEvents", "logs:GetLogEvents"],
          "Resource": ["arn:aws:logs:<REGION>:<ACCOUNT_ID>:log-group:<LOG_GROUP_PREFIX>*"]
        }
      ]
    }
    ```

    VERIFY: `logs:DescribeLogGroups` and `logs:GetQueryResults` do not support
    resource-level scoping on every account; if a call is denied, move those two to
    a statement with `"Resource": "*"` rather than widening the log-group list.
  - session duration ≤ `<8_HOURS>`.
- [ ] **Not** `ReadOnlyAccess`: it includes `s3:GetObject`, `dynamodb:Scan` and
  other data reads an ops agent does not need.
- [ ] Per engineer: a named CLI profile, signed in with `aws sso login --profile
  ops-reader-<ACCOUNT>`. No long-lived access keys. → `AWS_OPS_READER_PROFILE`.
- [ ] Unattended: a role assumed through OIDC from CI (see `04-pipeline/`), never
  an access key in a variable.

**Prove the write is denied**

```bash
export AWS_PROFILE=$AWS_OPS_READER_PROFILE
aws sts get-caller-identity                                             # shows the ops-reader role
aws cloudwatch describe-alarms --state-value ALARM --max-items 1        # works
aws ec2 stop-instances --instance-ids <ANY_INSTANCE_ID> --dry-run       # must be UnauthorizedOperation
aws iam simulate-principal-policy --policy-source-arn <OPS_READER_ROLE_ARN> \
  --action-names ecs:UpdateService cloudwatch:SetAlarmState rds:RebootDBInstance secretsmanager:GetSecretValue \
  --query 'EvaluationResults[].[EvalActionName,EvalDecision]' --output table   # every row implicitDeny
```

`--dry-run` makes EC2 check the permission without acting; the simulator does the
same for any action, without calling the service at all. A human runs both: the
simulator needs `iam:SimulatePrincipalPolicy`, which the agent's role should not have.

**Rotate**: Identity Center sessions expire on their own. To cut access at once,
remove the user's assignment to the permission set; existing sessions end at
their expiry, so keep the duration short.

---

## Google Cloud — viewer service account, used by impersonation

**Create**

- [ ] A service account `ops-reader@<PROJECT_ID>.iam.gserviceaccount.com` with
  only the viewer roles the agent needs, on `<PROJECTS>`:
  `roles/logging.viewer` (not `privateLogViewer`: that adds Data Access audit
  logs), `roles/monitoring.viewer`, `roles/errorreporting.viewer`,
  `roles/cloudtrace.user` (VERIFY: on your org it grants read access to traces;
  there is no narrower trace role), and per service `roles/run.viewer`,
  `roles/cloudsql.viewer`, `roles/container.viewer` as needed.
- [ ] **Not** `roles/viewer`: it is project-wide and grows with every new API.
- [ ] **No key file.** Grant each engineer `roles/iam.serviceAccountTokenCreator`
  on that one service account, and have them build impersonated credentials:

  ```bash
  gcloud auth application-default login \
    --impersonate-service-account=ops-reader@<PROJECT_ID>.iam.gserviceaccount.com
  ```

  → `GCP_OPS_READER_ADC` = the path the command prints. The audit log shows both
  the engineer and the service account.
- [ ] Organisation policy `iam.disableServiceAccountKeyCreation` on, if you can.

**Prove the write is denied**

```bash
SA=ops-reader@<PROJECT_ID>.iam.gserviceaccount.com
gcloud logging read 'severity>=ERROR' --freshness=1h --limit=1 --project <PROJECT_ID> --impersonate-service-account=$SA   # works
gcloud logging metrics create agent-write-test --log-filter='severity>=ERROR' \
  --project <PROJECT_ID> --impersonate-service-account=$SA                                          # must be PERMISSION_DENIED
gcloud run services update <ANY_SERVICE> --region <REGION> --update-labels=agent-write-test=1 \
  --project <PROJECT_ID> --impersonate-service-account=$SA                                          # must be PERMISSION_DENIED
```

**Rotate**: impersonated credentials last an hour and refresh from the engineer's
own login. To revoke one person, remove their Token Creator binding; to revoke
everyone, disable the service account.

---

## Sentry — read-scoped user auth token

**Create**

- [ ] *User settings → Personal Tokens* (User Auth Tokens): a token named
  `agent-readonly-<NAME>` with **only** `org:read`, `project:read`, `team:read`,
  `event:read`. No `:write` or `:admin` scope. → `SENTRY_AUTH_TOKEN`.
- [ ] Start the MCP server with `--skills inspect` (already in
  `mcp/sentry.mcp.json`): `triage` and `project-management` tools update issues
  and alert rules, and `seer` starts an AI analysis that Sentry bills for.
- [ ] Limit it to one organisation: `SENTRY_ORG` in the template, or
  `<org>/<project>` to pin a single project.
- [ ] Self-hosted: `SENTRY_HOST=sentry.example.internal` in the server's `env`.
- [ ] Organisation auth tokens (`sntrys_…`) are for CI release uploads. Do not
  give one to an agent.
- [ ] Check *Security & Privacy → Data Scrubber* is on: events carry request
  data and user context, and everything the token can read can reach the model.

**Prove the write is denied**

```bash
S=https://sentry.io/api/0          # or https://sentry.example.internal/api/0
curl -s -H "Authorization: Bearer $SENTRY_AUTH_TOKEN" "$S/organizations/<ORG>/projects/" | head -c 200   # works
curl -s -o /dev/null -w '%{http_code}\n' -XPUT -H "Authorization: Bearer $SENTRY_AUTH_TOKEN" \
  -H "Content-Type: application/json" -d '{"status":"resolved"}' \
  "$S/organizations/<ORG>/issues/?id=<ANY_ISSUE_ID>"                                                      # must be 403
```

**Rotate**: create a new token, swap the secret, delete the old one under
*Personal Tokens*. Sentry user tokens do not expire on their own: put the
rotation date in the matrix.
