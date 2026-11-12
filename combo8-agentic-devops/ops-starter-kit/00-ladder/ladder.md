# The read, recommend, act ladder

Agents earn trust in steps. Each rung gives an agent one more kind of action, and
the agent only moves up when there is evidence it handled the rung below. This
page is the one-page version: print it, pin it next to the on-call rota and keep
it up to date.

## What never changes, on any rung

Four rules. They are the same four in the kit `README.md` and in the rules file
(`CLAUDE.md.example`, `AGENTS.md.example`); the team playbook regroups them
(`06-playbook/team-playbook.md` says how).

1. **No direct write access to production.** Not on rung 1, not on rung 3.
2. **Changes arrive only as merge requests** in the IaC/config repo. GitOps (Argo CD,
   or whatever your stack runs) applies what was merged.
3. **A human gates every deploy.** The agent can draft, explain and recommend.
   A named person merges and promotes.
4. **Stop and ask on anything destructive** — delete, drain, scale to zero, restart,
   rollback, force-push, data migration, silencing an alarm. The list lives in
   `05-self-heal/` and in `01-access/settings/settings.example.json`.

The rules are not the controls. What holds them is **a credential that matches
the rung**: a rung-1 agent holds read-only tokens. A prompt saying "read-only" is
not a control; the token is.

## The three rungs

| | Rung 1 — Read | Rung 2 — Recommend | Rung 3 — Act under policy |
|---|---|---|---|
| **The agent may** | Query monitoring, logs, cluster state, pipelines. Summarise, correlate, explain. | Everything on rung 1, plus draft a change as a merge request on a feature branch. | Everything on rung 2, plus run one named, pre-agreed action for one named class of event. |
| **The agent may not** | Change anything anywhere: no commit, push or MR. It may *describe* a change in its note. | Merge, approve its own MR, deploy, or touch a protected branch. | Anything outside the written policy. Anything destructive without a human. |
| **Output lands in** | A triage note, a finding, a chat reply — including a proposed change written out as text, marked "proposed, not applied". | An MR with evidence, risk and rollback in the description. | An MR (preferred) or a single logged action, plus a notification to the approver. |
| **Credentials** | Read-only tokens: Zabbix read-only user, index-scoped Elastic key, `view` ServiceAccount, Argo CD `role:readonly`, Grafana Viewer, GitLab Reporter. | Rung 1 plus a GitLab identity that can push feature branches and open MRs, with protected branches and required human approval. | Rung 2 plus the one extra permission the policy names, and nothing else. |
| **Claude Code controls** | `settings.example.json` as shipped: deny rules, the `block_mutating_ops.py` hook, MCP servers in read-only mode. `git push` and `glab mr create` are already `ask` — on every rung, never `allow` — and the rung-1 token cannot push anyway. | The same settings file. Nothing moves out of `deny`; the `ask` prompt on `git push` and `glab mr create` is now the human gate on the way out. (Using the GitLab MCP server for MRs instead? See `01-access/settings/README.md` → "Moving to rung 2".) | Rung 2 controls plus the policy's kill switch, checked before every action. |
| **Rules file says** | `Current rung: **Read**` — describe changes, do not commit, push or open MRs. | `Current rung: **Recommend**` — open MRs on `agent/…` branches. | `Current rung: **Act under policy**`, naming the merged policy. |
| **Typical ops tasks** | "Why did the DB alarm fire at 03:10?" "Which triggers fired most last month?" | "Propose a Zabbix trigger for connection-pool saturation." "Bump the chart version and show the Helm diff." | "When a known-flaky job fails with the known error, retry it once." |
| **Workshop module** | M60–M63 | M62–M64 | M65 (design only) |

Going from rung 1 to rung 2 changes two things, each in a reviewed MR: the GitLab
credential (it can now push feature branches and open MRs) and the `Current rung`
line in the rules file. The Claude Code settings stay as shipped.

## Moving up a rung

An agent moves up only when all of these are true. Write the evidence down in the
agent inventory entry (`05-self-heal/`), not in a chat thread.

1. **Time at the rung.** At least `<N_WEEKS>` weeks of real use at the current rung.
2. **Track record.** Its outputs were reviewed and the error rate is known — for
   example "of 40 triage notes, 3 had a wrong root cause and none led to a bad action".
3. **A named owner** who will answer for it, and a reviewer for its MRs.
4. **Rollback tested.** For rung 3, the rollback for the one allowed action has been
   run for real, in a non-production environment, at least once.
5. **Kill switch tested.** Someone other than the owner has switched it off.

## Moving down a rung

Any of these drops the agent one rung immediately, no discussion needed:

- It took, or tried to take, an action outside its rung (the hook log or a denied
  permission prompt is the evidence).
- A recommendation it made was merged and caused an incident.
- Its credential was found to be broader than the matrix says.

Moving down is not a punishment. It is what makes moving up safe to agree to.

## One-line test

> "If this agent is wrong at 03:00, what is the worst thing that happens, and who
> finds out?"

If the answer is "it writes a wrong note and someone reads it in the morning",
rung 1 is fine. If the answer involves production changing, you are not on rung 1
any more — check that the credentials and the policy say so too.
