# Human-visible and agent-visible alarm channels

Preventative alarms fire early, by design. Sent to the pager, they become noise within a fortnight and get muted, and you are back where you started. So the kit separates two audiences.

| | Human-visible | Agent-visible |
|---|---|---|
| **What goes there** | Something a person must act on within the paging or ticket SLA | Leading indicators, trends, "this is drifting" signals |
| **Examples** | Sessions above 85 % of usable for 10 minutes; disk will fill in 4 hours | Idle-in-transaction sessions above 20 for 30 minutes; error category new since yesterday's deploy |
| **Delivery** | Pager, on-call chat, ticket queue — as today | A queue, topic, label or mailbox the agent reads. Never a pager |
| **Who reads it** | On-call engineer | The agent, on a schedule, at the **read** rung of the ladder |
| **What the reader may do** | Anything the runbook allows | Summarise, correlate, and draft. Never acknowledge, close, suppress or silence: those hide signal from humans |
| **Output** | Action, incident, ticket | A daily digest posted to the team channel, and draft MRs for triggers worth promoting |

## Rules

1. **Tag every trigger with its audience.** `audience: human` or `audience: agent` as a Zabbix trigger tag or a Grafana label. The templates in `templates/` already do this. Route on the tag, not on severity.
2. **Promotion is a human decision.** When an agent-visible signal keeps proving useful, the digest proposes moving it to `audience: human` in a draft MR. A person merges it.
3. **Demotion is too.** The noise review (`prompts/alarm-noise-review.md`) proposes moving pager noise to the agent channel. A person merges that as well.
4. **The agent channel is not a dumping ground.** If nobody reads the digest for two weeks, the channel has failed. Review it in the monthly noise review like any other trigger.
5. **Acknowledging is a write.** The agent never acknowledges or closes a problem in either channel. An acknowledged problem looks handled to the next human, so the agent would be hiding signal.

## Wiring it

- **Zabbix:** add a trigger action whose condition is *tag `audience` equals `agent`*. Its operation sends to a media type the agent can read, such as a webhook into a queue or a dedicated mailbox. Keep the existing paging actions conditioned on `audience` equals `human`, or on the absence of the tag during migration.
- **Grafana:** add a notification-policy route matching `audience = agent` that points at a contact point the agent reads, such as a webhook. Keep human routes unchanged.
- **The digest:** a scheduled read-only job (for example a `claude -p` run with only read tools, the same shape as `04-pipeline/gitlab-ci.diagnose.yml`) reads the last 24 hours of the agent channel. It posts one message: what fired, what is trending, and which signals it proposes promoting.

Placeholders to decide as a team: `<AGENT_CHANNEL_NAME>`, `<DIGEST_TIME_UTC>`, `<DIGEST_POSTED_TO>`.
