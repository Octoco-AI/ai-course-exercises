# Prompt — alarm-noise review

A monthly review that pairs with the preventative-alarms workflow. Adding preventative triggers without removing noisy ones only moves the problem. Run it on an **aggregated export** of the last 30 days of alarm events, one row per trigger, never on the raw event stream.

## Produce the input

From Zabbix (problem events) or Grafana (alert state history), export or query one row per trigger with:

| Column | Meaning |
|---|---|
| `trigger` | Name, or a stable id |
| `severity` | As configured |
| `audience` | `human` or `agent` tag, if you use them (see `../alarm-channels.md`) |
| `fired` | Times it went into problem/firing state in 30 days |
| `median_duration_min` | Median time in problem state |
| `auto_resolved_under_5m_pct` | Share that cleared on their own within 5 minutes |
| `acknowledged_pct` | Share a human acknowledged |
| `linked_to_incident` | Times it appeared in an incident or ticket |
| `pages_out_of_hours` | Times it paged outside working hours |

A spreadsheet or CSV is fine. If it has more than ~150 rows, review one host group at a time.

## The prompt

---

Below is an aggregated 30-day alarm export for **<TEAM_OR_HOST_GROUP>**. Classify every trigger into exactly one of:

- **keep**: fires rarely, humans act on it, and it links to real incidents.
- **tune**: real signal, wrong threshold or duration. Propose the new threshold or `for`/duration and say what it would have done to the 30-day count.
- **re-route**: real signal, but nobody needs to act within the paging SLA. Move it to the agent-visible channel or a ticket.
- **delete**: no incident link, mostly auto-resolves, nobody acknowledges it. Say what would tell us we were wrong to delete it.
- **unclear**: say what data would decide it.

Rules:

- Base every verdict on the columns. Quote the numbers.
- A trigger with `linked_to_incident > 0` is never **delete**, at most **tune**.
- Do not edit triggers, acknowledge problems or call any write tool. The output is a review, and it becomes a draft MR.

Output:

1. A table: trigger, verdict, the numbers that decided it, proposed change.
2. Expected effect: pages per month and out-of-hours pages per month, before and after.
3. A draft MR description for the changes, using the same headings as `.claude/skills/preventative-alarms/SKILL.md` step 5.

<PASTE AGGREGATED EXPORT HERE>

---

**What to expect.** The first run of this prompt finds a handful of triggers that page every week and that nobody has acted on in months. Deleting them is a team decision, not the agent's, which is why the output is a draft MR and not a change.
