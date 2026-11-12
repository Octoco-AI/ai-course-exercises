# Agent inventory entry — template

One entry per agent: every skill or sub-agent that can reach a system, every CI job that runs a model, every scheduled digest, every self-heal handler. The rule from the governance module holds: **if it can write, delete, send, spend or persist, it is in the inventory.** In ops, add one more: **if it holds a credential to a production system, even read-only, it is in the inventory.**

Commit entries to `<INVENTORY_PATH>` (one file per agent, or one table). A new agent and its inventory entry land in the **same MR**. No entry, no merge.

```markdown
## <agent-name>

| Field | Value |
|---|---|
| Name / identifier | <agent-name> |
| Type | skill / sub-agent / MCP server / CI job / scheduled workflow / self-heal handler |
| Harness | Claude Code (interactive) / Claude Code headless in GitLab CI / other |
| Definition | <path to SKILL.md, agent .md, .gitlab-ci.yml job, or policy> |
| Ladder rung | read / recommend / act (act requires a self-heal policy id) |
| Runs where | <laptop / runner tag / host> |
| Triggered by | <human / MR pipeline failure / schedule / alarm tag> |
| Tools (allowlist) | <exact list> |
| Tools explicitly denied | <list> |
| MCP servers and their read-only control | <server: control, e.g. argocd: MCP_READ_ONLY=true; kubernetes: read_only + view SA> |
| Credentials | <each token: system, account, scope/role, where stored, expiry> |
| Can write to | <nothing / MR comments in project X / MRs to repo Y paths Z> |
| Destructive actions approved | none (see `05-self-heal/destructive-actions.md`) |
| Human in the loop | <who reviews what it produces, and when> |
| Kill switch | <variable or flag, and who may pull it> |
| Where each rule lives | tool list: <file>; deny rules: <file>; hook: <file>; token scope: <system>. Will the next person to edit this agent see each one? |
| Authorised by | <name or role, date> |
| Owner | <name or role: accountable if it goes wrong> |
| Last reviewed / next review | <YYYY-MM-DD> / <YYYY-MM-DD> |
```

---

## Example entries (synthetic)

## diagnose-failed-job

| Field | Value |
|---|---|
| Name / identifier | diagnose-failed-job |
| Type | CI job |
| Harness | Claude Code headless (`claude --bare -p`) in GitLab CI |
| Definition | `04-pipeline/gitlab-ci.diagnose.yml`, prompt `04-pipeline/prompts/diagnose-failed-job.md` |
| Ladder rung | recommend |
| Runs where | runners tagged `nonprod-docker` |
| Triggered by | a failed job in a merge request pipeline |
| Tools (allowlist) | Read, Grep, Glob |
| Tools explicitly denied | Bash, Edit, Write, NotebookEdit, WebFetch, WebSearch; `--permission-mode dontAsk` |
| MCP servers and their read-only control | none (`--bare` loads no MCP config) |
| Credentials | `ANTHROPIC_API_KEY` (masked, not protected, spend limit <LIMIT>); `DIAGNOSE_API_TOKEN` (project access token, Reporter, `api`, expires <DATE>) |
| Can write to | MR comments in this project, via `post-mr-note.sh`, not the agent |
| Destructive actions approved | none |
| Human in the loop | the MR author reads the comment; nothing acts on it automatically |
| Kill switch | CI/CD variable `DIAGNOSE_ENABLED=false`; anyone on the team |
| Where each rule lives | tool list and flags: the CI file; token scope: GitLab project settings; runner restriction: runner tag. All in one MR-reviewed file, except the token scope |
| Authorised by | <ROLE>, <DATE> |
| Owner | <ROLE> |
| Last reviewed / next review | <DATE> / <DATE + 90d> |

## incident-triage (+ network-, app-, db-investigator)

| Field | Value |
|---|---|
| Name / identifier | incident-triage; network-investigator; app-investigator; db-investigator |
| Type | skill + three sub-agents |
| Harness | Claude Code, interactive, on an engineer's machine |
| Definition | `.claude/skills/incident-triage/SKILL.md`, `.claude/agents/*-investigator.md` |
| Ladder rung | read (writes only the triage note, locally, after asking) |
| Runs where | engineer laptops |
| Triggered by | a human, during or after an incident |
| Tools (allowlist) | skill: Read, Grep, Glob, Agent, aggregator script, `git log/show/diff`; sub-agents: Read, Grep, Glob + named read-only MCP tools per layer |
| Tools explicitly denied | skill: Edit, NotebookEdit; sub-agents: everything not in their allowlist |
| MCP servers and their read-only control | zabbix: read-only user + DenyTool on write tools; kubernetes: `read_only = true` + view-role ServiceAccount; argocd: `MCP_READ_ONLY=true` + read-only account; grafana: `--disable-write` + Viewer service account; elastic: index-scoped read-only API key |
| Credentials | per engineer, read-only, listed in `01-access/` token checklist |
| Can write to | the local triage note file only |
| Destructive actions approved | none |
| Human in the loop | the engineer selects the hypothesis and decides every action |
| Kill switch | remove or rotate the read-only tokens; delete the skill from the repo |
| Where each rule lives | tool lists: the agent files (reviewed with the agent); deny rules and hook: `.claude/settings.json` and the hook script (reviewed when someone remembers them, so add them to the quarterly review) |
| Authorised by | <ROLE>, <DATE> |
| Owner | <ROLE> |
| Last reviewed / next review | <DATE> / <DATE + 90d> |
