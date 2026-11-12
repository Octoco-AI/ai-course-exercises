# Delegation buckets for ops work

Fill this in for **five tasks your team does every week**. Place each one on the
ladder (`ladder.md`) as it is *today*, not as you hope it will be. The useful
output is the last two columns: what could go wrong, and what evidence would move
the task up a rung.

Replace every `<PLACEHOLDER>`. Keep it in the team's repo next to the playbook and
revisit it monthly.

## The buckets

| Bucket | Means | Example |
|---|---|---|
| **Not yet** | Keep it human. Either the blast radius is too big or nobody can yet say what "good" looks like. | Database failover. |
| **Rung 1 — Read** | The agent gathers and summarises; a human decides and acts. | Morning review of overnight Zabbix problems. |
| **Rung 2 — Recommend** | The agent drafts the change as an MR; a human reviews, merges and deploys. | Tuning a noisy trigger threshold. |
| **Rung 3 — Act under policy** | One named action for one named class of event, with an approver, rollback and kill switch written down. | Retrying a known-flaky CI job once. |

## Worked example

| Task | How often, time per week | Systems touched | Bucket today | Why this bucket | What could go wrong | Evidence to move up | Owner |
|---|---|---|---|---|---|---|---|
| Review the triggers that fired most last week and decide which are noise | Weekly, ~2 h | Zabbix (read), Grafana (read), IaC repo for templates | Rung 1 — Read | Nobody has yet agreed what "noise" means; the agent's job is to rank and explain | The agent calls a real early warning "noise" and someone deletes it | Four weekly reports reviewed with no wrong "noise" calls → rung 2: agent drafts the threshold change as an MR | `<OWNER>` |

## Your five tasks

| Task | How often, time per week | Systems touched | Bucket today | Why this bucket | What could go wrong | Evidence to move up | Owner |
|---|---|---|---|---|---|---|---|
| `<TASK_1>` | `<FREQUENCY>`, `<HOURS>` | `<SYSTEMS>` | `<BUCKET>` | `<WHY>` | `<WORST_CASE>` | `<EVIDENCE>` | `<OWNER>` |
| `<TASK_2>` | `<FREQUENCY>`, `<HOURS>` | `<SYSTEMS>` | `<BUCKET>` | `<WHY>` | `<WORST_CASE>` | `<EVIDENCE>` | `<OWNER>` |
| `<TASK_3>` | `<FREQUENCY>`, `<HOURS>` | `<SYSTEMS>` | `<BUCKET>` | `<WHY>` | `<WORST_CASE>` | `<EVIDENCE>` | `<OWNER>` |
| `<TASK_4>` | `<FREQUENCY>`, `<HOURS>` | `<SYSTEMS>` | `<BUCKET>` | `<WHY>` | `<WORST_CASE>` | `<EVIDENCE>` | `<OWNER>` |
| `<TASK_5>` | `<FREQUENCY>`, `<HOURS>` | `<SYSTEMS>` | `<BUCKET>` | `<WHY>` | `<WORST_CASE>` | `<EVIDENCE>` | `<OWNER>` |

## Prompts if you are stuck

- What did you do last Tuesday that you would rather not have done?
- Which alert do you open the same three dashboards for every time?
- Which MR do you write that is mostly copying values from one place to another?
- Which pipeline failure do you recognise from the first line of the log?
- What do you hand to the newest person on the team because it is safe to get wrong?

## Sanity checks before you finish

- [ ] At least one task is in **Not yet**. If none is, you are being optimistic.
- [ ] Nothing is in **Rung 3** that is not already in **Rung 2** somewhere else.
- [ ] Every "what could go wrong" names a system and a consequence, not "it might be wrong".
- [ ] Every row has a named owner, not a team name.
