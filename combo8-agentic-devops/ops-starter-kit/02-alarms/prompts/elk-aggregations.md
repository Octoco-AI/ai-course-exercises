# Prompt — ELK aggregations, never raw logs

Use with the read-only Elasticsearch MCP connection (see `01-access/`). The API key behind it should be scoped to the indices named below and nothing else. Replace every `<PLACEHOLDER>`.

---

I am investigating **<INCIDENT_OR_ALARM_CLASS>** for service **<SERVICE_NAME>**. Impact began at **<IMPACT_START_UTC>**. Logs are in **<INDEX_PATTERN, e.g. logs-orders-*>**.

Rules for every query in this session:

- `size: 0` on every search. You read aggregations, not documents.
- No query without a time range on `@timestamp`.
- If you need examples of a message, ask me first. Then fetch at most 3 documents with `_source` limited to `@timestamp`, `log.level`, `error.type` and `message`.
- Never paste raw log lines into the conversation in bulk. If you catch yourself wanting to, say so and propose an aggregation instead.

Steps:

1. **Shape of the window.** Errors and warnings per hour for <LOOKBACK, default 7 days> before impact, split by `log.level`:

   ```json
   {
     "size": 0,
     "query": { "bool": { "filter": [
       { "term": { "service.name": "<SERVICE_NAME>" } },
       { "terms": { "log.level": ["ERROR", "WARN"] } },
       { "range": { "@timestamp": { "gte": "<WINDOW_START>", "lt": "<WINDOW_END>" } } }
     ] } },
     "aggs": { "per_hour": {
       "date_histogram": { "field": "@timestamp", "fixed_interval": "1h" },
       "aggs": { "by_level": { "terms": { "field": "log.level", "size": 5 } } }
     } }
   }
   ```

2. **What kinds of error.** For the six hours around impact, the top error types and the top message categories:

   ```json
   {
     "size": 0,
     "query": { "bool": { "filter": [
       { "term": { "service.name": "<SERVICE_NAME>" } },
       { "term": { "log.level": "ERROR" } },
       { "range": { "@timestamp": { "gte": "<IMPACT_MINUS_3H>", "lt": "<IMPACT_PLUS_3H>" } } }
     ] } },
     "aggs": {
       "by_type": { "terms": { "field": "error.type", "size": 10 } },
       "categories": { "categorize_text": { "field": "message", "size": 10 } }
     }
   }
   ```

   VERIFY: `categorize_text` needs a `text` field and is costly on large windows; keep the range tight. `error.type` and `service.name` are ECS field names, so change them if your mapping differs.

3. **When did each category start?** For the top three categories, a daily count over the full lookback. A category that appears days before impact is a leading signal. A warning that *stops* after a deploy deserves a look too: one team found their leak warnings vanished the day someone switched leak detection off.

4. **ES|QL alternative**, if your connection exposes ES|QL rather than query DSL:

   ```esql
   FROM <INDEX_PATTERN>
   | WHERE service.name == "<SERVICE_NAME>" AND log.level == "ERROR"
     AND @timestamp >= "<WINDOW_START>" AND @timestamp < "<WINDOW_END>"
   | STATS errors = COUNT(*) BY hour = BUCKET(@timestamp, 1 hour), error.type
   | SORT hour
   | LIMIT 500
   ```

   VERIFY: `BUCKET` syntax against your Elasticsearch version.

5. **Stop.** Return a short table per step and your reading of it. The sample answer for the synthetic incident is `sample-data/log-summary.json`.
