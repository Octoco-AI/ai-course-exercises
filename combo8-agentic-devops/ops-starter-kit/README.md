# Ops starter kit — agentic DevOps

A kit for ops and platform teams that run monitoring (Zabbix, Grafana), logs (ELK), CI (GitLab), GitOps (Argo CD and Helm) and Kubernetes, and want agents to help without handing them the keys. There is no lab: copy the kit into your own repository, replace the `<PLACEHOLDER>` values and adapt it. Everything here is meant to be used, not just read.

## The model: read → recommend → act

Agents earn trust in steps.

1. **Read.** Query monitoring, logs, cluster and pipeline state. Summarise, correlate, explain. Read-only tokens.
2. **Recommend.** Everything above, plus draft a change as a **merge request** (or an MR comment). A human reviews and merges.
3. **Act, under a written policy.** One named action for one named class of event, still by MR, with an approver, a rollback and a kill switch.

The four rules that never change, on any rung (the same four as `00-ladder/ladder.md`):

1. Agents never get direct write access to production.
2. Changes arrive only as merge requests.
3. A human gates every deploy and every sync.
4. Stop and ask on anything destructive (`05-self-heal/destructive-actions.md`).

Two working habits sit alongside them in the rules file and every skill: read-only by default, and no raw log dumps (aggregate first, and cite the query behind every piece of evidence). The team playbook (`06-playbook/`) writes all six down as its five rules.

At rung 1 the rules file tells the agent to *describe* a change rather than open an MR; at rung 2 it may open one. The Claude Code settings are the same on both rungs: `git push` and `glab mr create` are always `ask`.

## The kit by module

| Module | Directory | What you take home |
|---|---|---|
| **m60** The read, recommend, act ladder | `00-ladder/` | `ladder.md` (the one-pager), `delegation-buckets.md` (which ops work to delegate, review or keep), `CLAUDE.md.example` and `AGENTS.md.example` (the ops rules file: read-only by default, changes only as MRs, never write to production, stop and ask on anything destructive) |
| **m61** Safe access to the ops stack | `01-access/`, `.claude/skills/ops-*` | Read-only MCP templates for Zabbix, Elastic, Argo CD, Kubernetes, Grafana and GitLab (`mcp/`); deny rules for write tools (`settings/`); a PreToolUse hook that blocks mutating `kubectl`, `helm` and `argocd` verbs, with tests (`hooks/`); a view-role ServiceAccount (`k8s/`); the least-privilege matrix and token checklist; one skill per tool (`ops-zabbix`, `ops-elastic`, `ops-argocd`, `ops-kubernetes`, `ops-grafana`, `ops-gitlab`) on how to query it and what not to do |
| **m62** Observability gaps to preventative alarms | `02-alarms/`, `.claude/skills/preventative-alarms/` | The preventative-alarms skill (window → aggregate → compare → propose → draft MR); query prompts for Zabbix history, ELK aggregations and DB stats; trigger proposals as code (Zabbix template, Ansible task, Grafana alert rules); the alarm-noise review; human-visible versus agent-visible channels; an aggregation and back-test tool |
| **m63** Cross-stack incident triage | `03-triage/`, `.claude/skills/incident-triage/`, `.claude/agents/` | Three read-only investigator sub-agents (network, app, DB) and the orchestrating triage skill; triage-note and runbook templates; a prompt for loading an architecture map as context |
| **m64** Agents in the pipeline | `04-pipeline/`, `.claude/skills/mr-review/`, `.claude/skills/helm-diff-review/` | A GitLab CI diagnose-failed-job stage (Claude Code headless, read-only tools, masked or OIDC credentials, no deploy rights); MR review and Helm diff review skills; a read-only Argo CD sync and drift check; an npm and Maven dependency-check prompt; the GitOps-engine caveat |
| **m65** Semi-self-healing, safely | `05-self-heal/` | Self-heal policy template with a worked example (a log volume filling up); the ops destructive-actions list; an agent inventory entry template with examples. Design only |
| **m66** Team playbook | `06-playbook/` | A one-page team playbook with a "next 30 days — three actions" block and an adoption checklist for every item in this kit |
| — | `sample-data/` | One synthetic incident (database sessions exhausted after days of a slowly rising signal), so every workflow can be tried without a live stack. Its `answer-key/` is for marking runs, never for an agent |

## Install into your repository

The paths inside the skills and sub-agents (`02-alarms/…`, `03-triage/…`) assume the kit's directories sit at the **root of the repository you run Claude Code in**. A dedicated ops or config repository is the natural home. If you put them somewhere else, search and replace those paths in `.claude/`.

```bash
KIT=<PATH_TO>/ops-starter-kit
REPO=<PATH_TO_YOUR_REPO>

# 1. Copy the kit, but not its top-level README/FACILITATOR (keep your own README).
#    Leave out sample-data/ once you have real data.
rsync -a --exclude /README.md --exclude /FACILITATOR.md "$KIT"/ "$REPO"/

cd "$REPO"

# 2. Rules file: start from the example and edit it (00-ladder/).
cp 00-ladder/CLAUDE.md.example CLAUDE.md        # and/or AGENTS.md.example → AGENTS.md

# 3. Enforcement: deny rules and the PreToolUse hook (01-access/settings/README.md).
mkdir -p .claude/hooks
cp 01-access/settings/settings.example.json .claude/settings.json      # merge if you already have one
cp 01-access/hooks/block_mutating_ops.py .claude/hooks/ && chmod +x .claude/hooks/block_mutating_ops.py

# 4. MCP servers: copy only the entries you use into .mcp.json, then set the env vars
#    each one needs, per engineer and never committed (01-access/mcp/README.md).
cp 01-access/mcp/mcp.example.json .mcp.json

# 5. Find every value you still have to fill in.
grep -rnoE '<[A-Z][A-Z0-9_]*>' --include='*.md' --include='*.json' --include='*.yml' --include='*.yaml' --include='*.toml' . | sort -u

# 6. Run the kit's tests (python3, pytest; jq, curl and shellcheck for the pipeline tests).
python3 -m pytest 01-access/hooks 02-alarms/tests 04-pipeline/tests
```

Then, in Claude Code, run `/mcp` and check that every server is connected and shows only the tools you expect. The tool names in the sub-agents' `tools:` lists must match.

## Guardrails, and where each one is enforced

| Guardrail | Enforced by |
|---|---|
| Read-only by default | The **tokens** (`01-access/token-checklist.md`), MCP servers in read-only mode, and sub-agent tool allowlists |
| No mutating `kubectl`, `helm`, `argocd` | Deny rules in `.claude/settings.json` and the PreToolUse hook (`01-access/hooks/`) |
| No acknowledging or silencing alarms | Zabbix and Grafana write tools denied, read-only monitoring users |
| Changes only as MRs | Agent Git identities cannot merge or push to protected branches. `git push` and MR creation are `ask`, never `allow` |
| No deploy rights in CI | The diagnose job declares no `environment:`, runs on a non-production runner, and holds a Reporter-level token (`04-pipeline/`) |
| No raw log dumps | Skills refuse them; prompts use `size: 0` aggregations; `02-alarms/tools/aggregate_metrics.py` caps output |
| Stop and ask on destructive actions | `05-self-heal/destructive-actions.md`, mapped row by row to a deny rule, the hook or a token scope |
| Act only under policy | A merged `05-self-heal/self-heal-policy.md` per alarm class, with a kill switch, and an inventory entry per agent |

A prompt that says "read-only" is not a control. The token is.

## Try it on the sample data

```bash
python3 02-alarms/tools/aggregate_metrics.py sample-data/metrics-db-sessions.csv --bucket 1d --summary-only --baseline-buckets 1
```

```text
/preventative-alarms sample-data/incident-brief.md using sample-data/ as the data source. Do not read sample-data/answer-key/.
/incident-triage orders-api 5xx from 2026-10-14T13:15Z. Case data in sample-data/ — no live MCP servers today. Use log-summary.json, db-stats-snapshot.json, metrics-db-sessions.csv and helm-values.diff. Do not read sample-data/answer-key/.
/helm-diff-review sample-data/helm-values.diff
```

Check each run afterwards against `sample-data/answer-key/README.md` → "What a good run finds". The answer key is for people: the commands above name their inputs so that no agent reads it, and the settings deny it as a backstop.

## Conventions

- `<PLACEHOLDER>` marks every value you must set. Lines marked `VERIFY:` are details checked against vendor documentation when the kit was written. Re-check them against the versions you run.
- Hosts are `example.internal`. All ids, names and numbers in examples are invented.
