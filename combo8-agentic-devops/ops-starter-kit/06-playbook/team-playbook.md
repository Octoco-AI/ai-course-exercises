# <TEAM_NAME> — agentic ops playbook

Version <N>, <YYYY-MM-DD>. Owner: <NAME_OR_ROLE>. Reviewed: monthly at <MEETING>. Lives at `06-playbook/team-playbook.md` in `<REPO>`. Change it by MR.

> One page, down to the 30-day actions. The adoption checklist is an appendix. If the page grows past that, move the detail into the kit file it summarises and link to it.

## The five rules

> These are the ladder's four rules (`00-ladder/ladder.md`) plus the rules file's two working habits, regrouped for a team: rule 1 is the "read-only by default" habit, rule 3 joins "no direct write to production" and "a human gates every deploy", and rule 5 is the "no raw log dumps" habit. Nothing here adds to or relaxes the ladder.

1. **Read-only by default.** Agents get read-only tokens and read-only MCP servers. Write access is an exception, written down in a self-heal policy.
2. **Changes arrive as MRs.** An agent's only write is a merge request (or an MR comment). Nothing changes outside Git.
3. **Never write to production.** No agent holds a production deploy credential. Humans gate every deploy and every sync.
4. **Stop and ask on anything destructive.** The list is `05-self-heal/destructive-actions.md`. Enforced by `.claude/settings.json` and the PreToolUse hook, not only by prompts.
5. **No raw log dumps.** Aggregate first. Evidence cites its query.

## Where each workflow sits on the ladder

| Workflow | Rung today | Next rung when… | Owner |
|---|---|---|---|
| Querying Zabbix, ELK, Grafana, Kubernetes, Argo CD | read | — (stays read) | <ROLE> |
| Incident triage (`/incident-triage`) | read | — (humans act) | <ROLE> |
| Preventative alarms (`/preventative-alarms`) | recommend (draft MR) | — | <ROLE> |
| Diagnose failed MR jobs (CI) | recommend (MR comment) | — | <ROLE> |
| MR and Helm diff review | recommend | — | <ROLE> |
| Argo CD drift report | read | — | <ROLE> |
| <SELF_HEAL_CLASS> | design only | policy <SH-NNN> approved and 20 recommend-rung MRs merged unchanged | <ROLE> |

## Access we have granted

Standing credentials only. A token made for a workshop or a trial is revoked when it ends; until its standing replacement exists, write `to create` in the credential column and make creating it one of the 30-day actions.

| System | Agent credential | Scope | Expires | Stored in |
|---|---|---|---|---|
| Zabbix | <user> | read-only role on <host groups> | <DATE> | <SECRET_STORE> |
| Elasticsearch | <API key name> | read on `<index patterns>` | <DATE> | |
| Kubernetes | <ServiceAccount> | `view` on <namespaces>, Secrets excluded | <DATE> | |
| Argo CD | <account> | read-only on <projects> | <DATE> | |
| Grafana | <service account> | Viewer | <DATE> | |
| GitLab | <token> | <scope, role> | <DATE> | |

Full checklist: `01-access/`. The agent inventory is at <INVENTORY_PATH>.

**How a new agent gets approved:** <WHO_REVIEWS> reviews it, and the agent and its inventory entry (`05-self-heal/agent-inventory-entry.md`) land in the same MR. No entry, no merge. Moving an existing agent up a rung is an MR against its row in the ladder table above.

## GitOps ownership

<Which engine (Argo CD or Flux) owns which clusters and namespaces. Never both on the same resources.>

## Kill switches

- Diagnose job: CI/CD variable `DIAGNOSE_ENABLED=false`
- Self-heal classes: <variable or flag per policy>
- Everything: revoke the tokens in the table above. <WHO> can do it, at <WHERE>

## Next 30 days — three actions

| # | Action | Owner | Done by | Done when |
|---|---|---|---|---|
| 1 | <e.g. Install the read-only MCP servers and token set from 01-access for the on-call engineers> | | | <everyone on call has run one read-only query> |
| 2 | <e.g. Run /preventative-alarms on our last two incidents and merge at least one trigger MR> | | | <trigger live with audience tag> |
| 3 | <e.g. Turn on the diagnose-failed-job stage for one repository> | | | <five MR comments read and rated useful / not useful> |

Pick three, not ten. Each needs an owner and a date, and its "done when" must be something you can observe.

## Appendix — adoption checklist

Tick items as they reach your repo **and** get used once for real.

**m60 — the ladder**
- [ ] Ladder one-pager shared with the team (`00-ladder/`)
- [ ] Delegation buckets filled in for our ops work (`00-ladder/`)
- [ ] Ops rules file committed as `CLAUDE.md` / `AGENTS.md` (`00-ladder/`)

**m61 — safe access**
- [ ] `.mcp.json` with read-only servers for the tools we use (`01-access/`)
- [ ] Per-tool skills installed (`.claude/skills/ops-*`)
- [ ] `.claude/settings.json` deny rules committed
- [ ] PreToolUse hook installed, and its tests run on our machines
- [ ] Least-privilege matrix filled in
- [ ] Token checklist complete: Zabbix read-only user, index-scoped Elastic key, view-role ServiceAccount, read-only Argo CD account, read-only GitLab token

**m62 — preventative alarms**
- [ ] `/preventative-alarms` run on one real incident
- [ ] One trigger MR merged, with an `audience` tag
- [ ] Agent-visible channel and daily digest wired (`02-alarms/alarm-channels.md`)
- [ ] First monthly alarm-noise review held

**m63 — triage**
- [ ] Investigator sub-agents' tool lists matched to our MCP server names
- [ ] Architecture map export available to the triage skill
- [ ] First triage note committed to `docs/triage/`
- [ ] One runbook written from the template

**m64 — pipeline**
- [ ] `gitlab-ci.diagnose.yml` included in one repository, on a non-production runner
- [ ] Argo CD drift report scheduled
- [ ] `mr-review` and `helm-diff-review` used on a real MR
- [ ] Dependency-check prompt run on one npm and one Maven project

**m65 — semi-self-healing (design)**
- [ ] Destructive-actions list tuned and committed
- [ ] Inventory entry for every agent above
- [ ] One self-heal policy drafted and reviewed, even if the answer is "not yet"

**m66 — this playbook**
- [ ] Playbook merged, owner named, monthly review in the calendar
