# Read-only MCP server templates

One `.mcp.json` per tool, plus `mcp.example.json` with all six. Copy the entries
you need into the `.mcp.json` at your repo root. Every credential arrives through
`${ENV_VAR}` expansion — there is no literal token in any file here, and there
must never be one in yours.

| File | Server | Transport | Read-only switch in the file |
|---|---|---|---|
| `zabbix.mcp.json` | Zabbix 8.0 built-in MCP server | HTTP | None in the client — it lives on the server (`DenyTool`) and in the token's user role |
| `elastic.mcp.json` | Elastic Agent Builder MCP endpoint (Kibana) | HTTP | None in the client — it is the API key's privileges |
| `argocd.mcp.json` | `argoproj-labs/mcp-for-argocd` (`argocd-mcp`) | stdio via `npx` | `MCP_READ_ONLY=true` |
| `kubernetes.mcp.json` | `containers/kubernetes-mcp-server` | stdio via `npx` | `read_only = true` in `kubernetes-mcp.toml` |
| `grafana.mcp.json` | `grafana/mcp-grafana` | stdio via `uvx` | `--disable-write` |
| `gitlab.mcp.json` | GitLab built-in MCP server (`/api/v4/mcp`) | HTTP | None — toolset header narrows what is listed; the user's project role is the control |

The server keys (`zabbix`, `elastic`, `argocd`, `kubernetes`, `grafana`, `gitlab`)
matter: Claude Code names tools `mcp__<key>__<tool>`, and the deny rules in
`../settings/settings.example.json` and the `allowed-tools` lines in the
`.claude/skills/ops-*` skills use those names. Rename a key and you must rename
the rules too.

## Environment variables to set

Set these in the shell that starts Claude Code — from a secrets manager, a
`direnv` file outside the repo, or your CI's masked variables. Never commit them.

| Variable | Example value | Used by |
|---|---|---|
| `ZABBIX_MCP_URL` | `https://zabbix-mcp.example.internal:<PORT>/mcp` | zabbix |
| `ZABBIX_API_TOKEN` | your own Zabbix API token | zabbix |
| `KIBANA_URL` | `https://kibana.example.internal` (no trailing slash) | elastic |
| `ELASTIC_MCP_API_KEY` | the encoded API key | elastic |
| `ARGOCD_BASE_URL` | `https://argocd.example.internal` | argocd |
| `ARGOCD_API_TOKEN` | token for the read-only account | argocd; also `04-pipeline/argo-drift-check.sh`, which passes it to the CLI as `ARGOCD_AUTH_TOKEN` |
| `KUBE_MCP_CONFIG` | absolute path to `kubernetes-mcp.toml` | kubernetes |
| `OPS_READER_KUBECONFIG` | absolute path to a kubeconfig holding the `ops-reader` token | kubernetes |
| `GRAFANA_URL` | `https://grafana.example.internal` | grafana |
| `GRAFANA_SERVICE_ACCOUNT_TOKEN` | Viewer service-account token | grafana |
| `GITLAB_URL` | `https://gitlab.example.internal` | gitlab |

Claude Code deliberately expands some well-known credential variables (its own
`ANTHROPIC_*` keys, cloud-provider tokens and a few others) to an empty string in a
remote server's `url` and `headers`, so a project file cannot leak them. The names
above are outside that set. If a server answers `401` and the variable is set,
check that you have not reused one of those reserved names.

## Per-user tokens or a service account?

**Default to per-user tokens for people at a keyboard.** Each engineer's agent
acts as that engineer, with that engineer's read-only credential. The audit log
in Zabbix, Kibana, Argo CD and GitLab then says who asked, and revoking one
person's access revokes their agent's too. Zabbix's built-in server requires
this: each user configures their own API token. GitLab's server prefers OAuth,
which is per-user by construction.

**Use a service account only for unattended runs** — a CI job, a scheduled
report, a triage agent triggered by an alert. Then:

- one service account per agent, not one shared "ai" account;
- the account is read-only on rung 1, and its scope is written in
  `../least-privilege-matrix.md`;
- tokens are short-lived or have an expiry, and live in the CI's masked
  variables or a secrets manager;
- the agent inventory entry names the account and its owner.

Either way, the credential is the boundary. The MCP switch and the Claude Code
deny rules are there to stop honest mistakes early and with a clear message.

## Where each read-only switch lives

Three layers, outermost first. You want at least the first and second for every
tool; the third is the backstop.

| Tool | 1. Credential (the real boundary) | 2. Server switch | 3. Claude Code (`settings.example.json`) |
|---|---|---|---|
| Zabbix | API token of a user whose role only allows `*.get` API methods and read on the chosen host groups | `DenyTool` lines in `zabbix_mcp_server.conf` for every `problem_*` write and `maintenance_*` write | Deny `mcp__zabbix__problem_acknowledge`, `…__maintenance_create` and the rest |
| Elastic | API key with `read` and `view_index_metadata` on named index patterns only, plus `feature_agentBuilder.read` | None documented | Deny the Agent Builder tools that create visualisations, cases or run workflows |
| Argo CD | Local account bound to `role:readonly` | `MCP_READ_ONLY=true` | Deny `mcp__argocd__sync_application` and the other write tools; `argocd app sync` etc. in Bash |
| Kubernetes | `ops-reader` ServiceAccount bound to `view` (`../k8s/ops-reader-rbac.yaml`) | `read_only = true`, `disable_destructive = true`, Secrets denied | Deny `mcp__kubernetes__resources_delete` and friends; hook blocks mutating `kubectl`/`helm` |
| Grafana | Service account with the Viewer role | `--disable-write` | Deny `update_dashboard`, `alerting_rules_write` and the other write tools |
| GitLab | Reporter role (rung 1); Developer with protected branches and required approvals (rung 2) | `X-Gitlab-Enabled-Mcp-Server-Toolsets` limits which tools are listed — not a permission | Deny `accept_merge_request`, `save_*`, `add_commit` and the other write tools |

### Zabbix server-side snippet

The official server ships with some read tools denied (`item_get`, `lld_get`,
`interface_get`, `macro_get`, `history_get`). Preventative alarms (M62) need
`item_get` and `history_get`, so remove those two lines; keep `macro_get` denied
because macros can hold credentials. Then deny the writes:

```ini
# zabbix_mcp_server.conf — VERIFY: parameter syntax against the 8.0 manual's
# "Zabbix MCP server" configuration page before you rely on it.
DenyTool=problem_acknowledge
DenyTool=problem_unacknowledge
DenyTool=problem_close
DenyTool=problem_annotate
DenyTool=problem_change_severity
DenyTool=problem_suppress
DenyTool=problem_unsuppress
DenyTool=maintenance_create
DenyTool=maintenance_update
DenyTool=maintenance_delete
DenyTool=macro_get
```

If your MCP client does not support form elicitation, the server applies changes
**without** an approval prompt. Do not rely on the prompt either way (VERIFY:
whether your Claude Code version supports MCP form elicitation): deny the write
tools on the server.

**On Zabbix 7.x or older?** The built-in server only supports its own Zabbix
version. The community `initMAX/zabbix-mcp-server` covers 5.0–8.0; set
`read_only = true` under each `[zabbix.<name>]` section of its `config.toml`, run
it over HTTP on loopback, and point `ZABBIX_MCP_URL` at it. Its config file holds
the Zabbix API token, so it belongs to one person or one service account — not a
shared host.

### Elastic notes

- The Agent Builder MCP endpoint is generally available from Elastic Stack 9.3
  (preview in 9.2). The older standalone `elastic/mcp-server-elasticsearch` is
  deprecated and receives only critical security fixes; do not start new work on it.
- For a non-default Kibana space, the path is `${KIBANA_URL}/s/<SPACE_ID>/api/agent_builder/mcp`.
- Some teams run their own Elasticsearch MCP service on older clusters. The same
  rule applies: an index-scoped, read-only API key is the boundary.

### Argo CD notes

- Pin `argocd-mcp` at **0.9.0 or later**. 0.9.0 fixed an advisory affecting the HTTP
  and SSE transports (the listener now binds to loopback and needs
  `MCP_AUTH_TOKEN` when widened). This template uses stdio, which opens no listener.
- If your platform ships **Flux** as its GitOps engine, Argo CD can run alongside,
  but never let two engines manage the same resources. Point the agent at
  whichever engine owns the app you are asking about.

## CLI or MCP?

Both work. Pick per task, not per team.

| Prefer the **CLI** (`kubectl`, `helm`, `argocd`, `glab`, `curl`) when… | Prefer **MCP** when… |
|---|---|
| The output is already compact and you know the exact command | The agent needs to explore — find the dashboard, the index, the trigger |
| You want the hook to see the exact command text | There is no good CLI (Zabbix, Kibana, Grafana) |
| The same command will later run in CI | You want a server-side read-only switch as a second layer |
| You need `jq`, `sort`, `uniq -c` to aggregate before reading | You want per-user OAuth instead of a token on disk (GitLab) |

Two rules apply either way: aggregate before reading, and the identity behind the
call is read-only. An analysis-only tool such as `k8sgpt analyze` is another
reasonable read-only source for Kubernetes triage; it explains, it does not fix.

## Unverified details

Checked against vendor docs and repos in November 2026; re-check before
production use. Marked `VERIFY:` where they appear.

- VERIFY: the exact `DenyTool=` line syntax for `zabbix_mcp_server.conf`, and the server's default `ListenPort`.
- VERIFY: Claude Code's name for Elastic tools whose MCP names contain dots (`platform.core.search`). The deny rules and the `ops-elastic` skill assume dots become underscores: `mcp__elastic__platform_core_search`.
- VERIFY: that `kubernetes-mcp-server` honours `KUBECONFIG` from its environment (standard client-go behaviour). If not, set `kubeconfig = "<ABSOLUTE_PATH>"` in `kubernetes-mcp.toml`.
- VERIFY: the package versions pinned here (`argocd-mcp@0.9.0`, `kubernetes-mcp-server@0.1.2`, `mcp-grafana@2.2.0`) were current in November 2026. Pin to the version you reviewed, not to `latest`.
- VERIFY: whether GitLab's fine-grained personal access token can be limited to read-only MCP tools. Until you have confirmed it, treat the user's project role as the only server-side control.
