---
name: ops-elastic
description: Query Elasticsearch read-only through the Elastic Agent Builder MCP endpoint, using ES|QL aggregations over a fixed time window before ever reading raw log lines. Use when the user asks what errors spiked, which service logged what around an incident, or how log volume changed.
allowed-tools: mcp__elastic__platform_core_list_indices mcp__elastic__platform_core_get_index_mapping mcp__elastic__platform_core_index_explorer mcp__elastic__platform_core_execute_esql mcp__elastic__platform_core_generate_esql mcp__elastic__platform_core_search mcp__elastic__platform_core_get_document_by_id
---

# Elasticsearch, read-only

You have read access to the indices the API key allows, through the `elastic` MCP
server. You cannot write. Tools that create visualisations, Discover sessions or
cases, or run workflows and connectors, are denied — do not try them.

<!-- VERIFY: tool names assume Claude Code turns the dots in `platform.core.search`
     into underscores. Check the names `/mcp` shows and fix allowed-tools if not. -->

## Before the first query

1. Confirm the **time window**: the incident time ± 30 minutes unless told otherwise.
   Every query carries an explicit `@timestamp` range. Never query "all time".
2. Find the right index once: `list_indices`, then `get_index_mapping` on the one
   you will use, so you know the real field names (`service.name` or `app`?
   `log.level` or `level`?). Do not guess field names.

## Aggregate first, always

Start with counts, not documents. ES|QL via `execute_esql`:

```esql
FROM logs-app-*
| WHERE @timestamp >= TO_DATETIME("2026-01-01T02:40:00Z") AND @timestamp < TO_DATETIME("2026-01-01T03:40:00Z")
  AND log.level == "error"
| STATS errors = COUNT(*) BY service.name
| SORT errors DESC
| LIMIT 10
```

Then shape over time for the top service:

```esql
FROM logs-app-*
| WHERE @timestamp >= TO_DATETIME("2026-01-01T02:40:00Z") AND @timestamp < TO_DATETIME("2026-01-01T03:40:00Z")
  AND service.name == "<SERVICE>"
| STATS n = COUNT(*) BY bucket = BUCKET(@timestamp, 1 minute), log.level
| SORT bucket
```

Then the most common messages, not all of them:

```esql
... | EVAL msg = LEFT(message, 120)
    | STATS n = COUNT(*) BY error.type, msg | SORT n DESC | LIMIT 15
```

Only after that, and only if needed, read up to five sample documents for one
specific error, with `KEEP` limiting the fields to what you need.

## Never

- Never pull raw log lines in bulk into the conversation. Twenty lines is a lot.
- Never query without a time range or with `LIMIT` above 100 for raw rows.
- Never print fields that may hold personal data or secrets (headers, tokens,
  request bodies, user identifiers). Aggregate over them or drop them with `KEEP`.
- Never call a tool that creates or changes anything, even "just a visualisation".

## Hand back

The top error sources with counts, when each started and peaked (from the
time-bucketed query), the two or three dominant messages, and the exact ES|QL you
ran so a human can rerun it in Kibana. Say plainly if the data does not explain
the incident.
