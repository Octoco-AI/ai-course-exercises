# Prompt — Zabbix history, aggregated

Paste into Claude Code with the read-only Zabbix MCP server connected (see `01-access/`), or use it with an exported CSV and `02-alarms/tools/aggregate_metrics.py`. Replace every `<PLACEHOLDER>`.

---

I am investigating **<INCIDENT_OR_ALARM_CLASS>** on **<HOST_OR_HOST_GROUP>**. Impact began at **<IMPACT_START_UTC>**.

Use only read tools (`host_get`, `item_get`, `trigger_get`, `problem_get`, `history_get`). Do not acknowledge, close, suppress or annotate problems, and do not create maintenance windows. Each of those changes what humans see, so each counts as a write.

1. **Find the items, not the data.** Use `host_get` and `item_get` to list the items on <HOST_OR_HOST_GROUP> whose key or name matches <ITEM_PATTERN, e.g. pgsql.connections* or vfs.fs.size*>. Return a table: item id, key, units, update interval, history and trends retention. Stop there and show me the table before you fetch any values.
2. **Choose the resolution from the window.** The window is <LOOKBACK, default 14 days> before impact.
   - Up to 2 days: 5-minute buckets.
   - Up to 14 days: hourly buckets.
   - Longer: daily buckets, from trends rather than history.

   Fetch with explicit `time_from` / `time_till` and a `limit`. Never request a whole retention period. If an item's interval is 1m and the window is 14 days, that is ~20,000 points per item, so fetch in slices and aggregate each slice before moving on.
3. **Aggregate before you read.** For each item, return one row per bucket: min, avg, max, last. Keep the raw points out of the conversation. If a result would exceed 200 rows, re-bucket it coarser and tell me you did.
4. **Summarise each series** in one line: overall trend (slope per day), the first bucket that left its normal range, and whether any existing trigger (`trigger_get` on the same items) would have fired, and when.
5. **Stop.** Give me the summary table and your three most suspicious series, with the evidence. Do not propose triggers yet.

---

**Why this shape.** Zabbix history is the easiest place to flood an agent's context: one item at a one-minute interval is 1,440 points a day. Asking for item metadata first, then buckets, keeps the evidence readable and the bill small. VERIFY: the official Zabbix MCP server (8.0) lists `history_get` but no trends tool. On older versions, or with a community server, check which tools exist (`/mcp` in Claude Code) and adjust the tool names above.
