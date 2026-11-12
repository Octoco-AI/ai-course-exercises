---
name: ops-zabbix
description: Query Zabbix read-only through its MCP server — problems, triggers, hosts, items and history — aggregating before reading and staying inside a time window. Use when the user asks what fired, why an alarm triggered, which triggers are noisiest, or what a metric did around an incident.
allowed-tools: mcp__zabbix__problem_get mcp__zabbix__trigger_get mcp__zabbix__host_get mcp__zabbix__hostgroup_get mcp__zabbix__template_get mcp__zabbix__item_get mcp__zabbix__history_get mcp__zabbix__maintenance_get mcp__zabbix__interface_get
---

# Zabbix, read-only

You have read access to Zabbix through the `zabbix` MCP server. You cannot and must
not change anything in Zabbix. `allowed-tools` above pre-approves the read tools;
the write tools are denied in settings and on the server.

## Before the first query

1. Confirm the **instance** (production or not) and the **time window**. If the user
   gave an incident time, use it ± 30 minutes. If not, ask — do not default to "all".
2. Confirm the **scope**: a host group, a host, or a trigger name. Resolve names to
   ids once with `hostgroup_get` / `host_get` and reuse the ids.

## Query well

- **Problems before history.** `problem_get` for the window tells you what fired,
  when and at what severity. Count by trigger and by host before you look at any
  single event.
- **Triggers next.** `trigger_get` on the triggers that fired, to read their
  expressions and thresholds. Quote the expression when you explain why it fired.
- **History last, and narrow.** `history_get` only for the few items behind those
  triggers, only for the window, with a `limit`. Pass the item's value type
  in the `history` parameter (take it from `item_get`): the default is unsigned
  integers, so a float item silently returns nothing. Summarise as min, max, mean
  and the time of the peak — do not paste the raw series.
- **Noisiest triggers** (weekly review): `problem_get` over the period, then count
  per trigger and per host, and report the top 10 with fire count, median duration
  and how many were resolved within five minutes. That last number is the
  flapping signal.
- **Maintenance matters.** Check `maintenance_get` for the window before calling a
  silence "missing" — a host in maintenance does not raise problems.

## Never

- Never acknowledge, close, suppress, change severity of or annotate a problem.
- Never create, update or delete maintenance. "Put the host in maintenance" is a
  human action; say so and draft the change for them.
- Never read user macros — they can hold credentials (`macro_get` is denied).
- Never fetch history for a whole host group or without a time window.

## Hand back

A short note: what fired (counts by trigger and host), the trigger expression in
plain words, what the underlying metric did (min/max/peak time), and anything
that looks like a gap — a metric that moved without an alarm. If the user wants
a change (new trigger, new threshold), hand off to the preventative-alarms work:
the change is drafted as a Zabbix template in an MR, never applied here.

If a tool is missing (the server denies `item_get` and `history_get` by default),
say which one and point the user to `01-access/mcp/README.md`.
