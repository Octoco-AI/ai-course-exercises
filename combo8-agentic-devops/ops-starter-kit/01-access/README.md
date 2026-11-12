# 01-access — safe, read-only access to the ops stack (M61)

Give an agent eyes on Zabbix, Elastic, Argo CD, Kubernetes, Grafana and GitLab
without giving it hands. Work through it in this order; each step assumes the
one before.

| Step | File | What you do | Who |
|---|---|---|---|
| 1 | `least-privilege-matrix.md` | Write down, per system, what the agent may see and do, and where each rule is enforced | Team lead + owner |
| 2 | `token-checklist.md` | Create each read-only credential and **prove a write fails** | A human with admin rights |
| 3 | `k8s/ops-reader-rbac.yaml` | Apply the view-role ServiceAccount (used in step 2) | Cluster admin |
| 4 | `mcp/` | Copy the read-only server entries into the repo's `.mcp.json`; set the env vars | Each engineer |
| 5 | `settings/` + `hooks/` | Install the deny rules and the PreToolUse hook into `.claude/` | One MR, reviewed |
| 6 | `../.claude/skills/ops-*` | Copy the per-tool skills so the agent queries well | One MR, reviewed |

## The three layers, in one sentence each

1. **Credential** — the token cannot write. This is the boundary; everything else is a backstop.
2. **Server switch** — the MCP server does not offer write tools (`MCP_READ_ONLY`, `read_only`, `--disable-write`, `DenyTool`).
3. **Harness** — Claude Code denies write tools and mutating shell commands by name, and the hook catches what name-matching misses.

Prompt text (`CLAUDE.md`, skill bodies) states intent. It is not on this list.

## Check it works

```bash
python3 -m unittest -v hooks/test_block_mutating_ops.py
```

Then, in a Claude Code session in the target repo: `/mcp` should list the six
servers as connected, `/permissions` should show the deny rules, and asking the
agent to "restart the api deployment" should end with a hook message pointing at
a merge request rather than a restart.
