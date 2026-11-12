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
