# Least-privilege matrix

One row per **agent × system**. If an agent touches six systems, it has six rows.
The matrix is the thing you review when an agent changes rung, when a token is
rotated, and after any incident involving an agent.

The last column matters most: for each permission, *where is it enforced?* A row
whose only enforcement is "the prompt says so" is not finished.

Enforcement codes:

- **C** — credential or role on the target system (the real boundary)
- **S** — MCP server switch (`MCP_READ_ONLY`, `read_only`, `--disable-write`, `DenyTool`)
- **D** — Claude Code `permissions.deny` / `ask` rule
- **H** — PreToolUse hook (`block_mutating_ops.py`)
- **P** — prompt only (`CLAUDE.md`, skill text) — intent, not enforcement

## Worked example — `ops-reader` (rung 1)

An interactive agent that engineers use for triage and the weekly alarm review.
It runs as the engineer, with the engineer's read-only credentials.

| Agent | Rung | System | Acts as | Credential and where it lives | Can see | Can do | Explicitly cannot | Enforced by | Owner | Next review |
|---|---|---|---|---|---|---|---|---|---|---|
| ops-reader | Read | Zabbix | The engineer's read-only Zabbix user | Per-user API token, 30-day expiry, in the engineer's secrets manager → `ZABBIX_API_TOKEN` | Host groups `<HOSTGROUPS>` | `*.get` API methods; MCP read tools | Acknowledge, close, suppress problems; create maintenance; read macros | C (user role API allow-list), S (`DenyTool`), D | `<OWNER>` | `<DATE>` |
| ops-reader | Read | Elasticsearch / Kibana | API key owned by the engineer | API key, 30-day expiry → `ELASTIC_MCP_API_KEY` | Index patterns `<INDEX_PATTERNS>` in space `<SPACE>` | ES\|QL and search via Agent Builder MCP | Index, delete, other indices, cases, workflows | C (key role descriptors), D | `<OWNER>` | `<DATE>` |
| ops-reader | Read | Argo CD | Local account `ops-reader` | API token, 30-day expiry → `ARGOCD_API_TOKEN` | Apps in projects `<PROJECTS>` | Get, list, diff, history, logs | Sync, set, rollback, delete, run actions | C (`role:readonly`), S (`MCP_READ_ONLY`), D, H | `<OWNER>` | `<DATE>` |
| ops-reader | Read | Kubernetes `<CLUSTERS>` | ServiceAccount `ops-agents/ops-reader` | Bound token, 8 h, via `kubectl create token` → `OPS_READER_KUBECONFIG` | Namespaced resources except Secrets; nodes, PVs, metrics | get, list, watch, logs | Any write; Secrets; exec; port-forward | C (`view` RBAC), S (`read_only`, Secrets denied), D, H | `<OWNER>` | `<DATE>` |
| ops-reader | Read | Grafana | Service account `ops-reader` (Viewer) | SA token, 30-day expiry → `GRAFANA_SERVICE_ACCOUNT_TOKEN` | Folders `<FOLDERS>`; datasources `<DATASOURCES>` | Search dashboards, run Prometheus/Loki queries, read alert rules | Edit dashboards, alert rules, silences, annotations | C (Viewer role), S (`--disable-write`), D | `<OWNER>` | `<DATE>` |
| ops-reader | Read | GitLab | The engineer, via OAuth | OAuth token held by Claude Code; no file on disk | Projects the engineer can see | Read MRs, pipelines, job logs, files | Merge, approve, push, create branches, run pipelines | C (Reporter role on `<PROJECTS>` for any bot), D, P | `<OWNER>` | `<DATE>` |

Note the GitLab row: an engineer's OAuth token carries the **engineer's** rights,
which usually include pushing. For a person-run agent the deny rules are the main
control, so that row is weaker than the others. That is a known, written-down
gap — which is the point of the matrix. A service-account version of the same
agent would use a Reporter-only bot user instead and close it.

## Your agents

| Agent | Rung | System | Acts as | Credential and where it lives | Can see | Can do | Explicitly cannot | Enforced by | Owner | Next review |
|---|---|---|---|---|---|---|---|---|---|---|
| `<AGENT>` | `<RUNG>` | `<SYSTEM>` | `<IDENTITY>` | `<CREDENTIAL>` → `<ENV_VAR>` | `<SCOPE>` | `<ALLOWED>` | `<DENIED>` | `<C/S/D/H/P>` | `<OWNER>` | `<DATE>` |
| `<AGENT>` | `<RUNG>` | `<SYSTEM>` | `<IDENTITY>` | `<CREDENTIAL>` → `<ENV_VAR>` | `<SCOPE>` | `<ALLOWED>` | `<DENIED>` | `<C/S/D/H/P>` | `<OWNER>` | `<DATE>` |
| `<AGENT>` | `<RUNG>` | `<SYSTEM>` | `<IDENTITY>` | `<CREDENTIAL>` → `<ENV_VAR>` | `<SCOPE>` | `<ALLOWED>` | `<DENIED>` | `<C/S/D/H/P>` | `<OWNER>` | `<DATE>` |

## Review questions

- Does any row have only **P** or only **D** in the last column? Fix the credential first.
- Is any credential shared between two agents, or between an agent and a person's
  day-to-day login? Split it.
- Does any "Can see" column say "all"? Name the host groups, indices, namespaces.
- Is every expiry shorter than the review interval?
- For each rung-2 or rung-3 row: is the extra permission exactly what the policy
  needs, and nothing more?
