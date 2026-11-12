# Prompt — database stats, aggregated in SQL

For session, connection and lock questions. The agent does not get a database connection in this kit. Either a human runs these queries with a monitoring role and pastes the *aggregated* result back, or your team adds a read-only database path later and records it in the agent inventory (`05-self-heal/agent-inventory-entry.md`).

Replace every `<PLACEHOLDER>`.

---

I am investigating **<INCIDENT_OR_ALARM_CLASS>** on database **<DB_NAME>** at **<DB_HOST>**. Below are aggregated query results taken at **<SNAPSHOT_TIME_UTC>**. Read them as evidence: say what they show, what they rule out, and what they do not tell us. Do not suggest killing sessions, changing settings or restarting anything. Those are human decisions on the destructive-actions list.

<PASTE RESULTS HERE>

---

## Queries to produce the results (PostgreSQL)

Run as a role with `pg_monitor`, never as a superuser. Every query aggregates. **None selects the `query` column**, which holds SQL text that may contain customer data.

```sql
-- 1. Sessions by application and state, with the oldest open transaction
SELECT application_name,
       coalesce(state, 'unknown')                       AS state,
       count(*)                                         AS sessions,
       max(now() - xact_start)                          AS oldest_xact_age
FROM   pg_stat_activity
WHERE  datname = '<DB_NAME>'
GROUP  BY 1, 2
ORDER  BY sessions DESC;

-- 2. The limits that matter
SELECT name, setting
FROM   pg_settings
WHERE  name IN ('max_connections', 'superuser_reserved_connections',
                'idle_in_transaction_session_timeout', 'statement_timeout');

-- 3. What idle-in-transaction sessions are waiting on
SELECT wait_event_type, wait_event, count(*) AS sessions
FROM   pg_stat_activity
WHERE  datname = '<DB_NAME>' AND state = 'idle in transaction'
GROUP  BY 1, 2
ORDER  BY sessions DESC;

-- 4. Sessions waiting on locks (count only)
SELECT count(*) AS locks_waiting
FROM   pg_locks
WHERE  NOT granted;
```

## Equivalents elsewhere

- **MySQL / MariaDB:** `SHOW GLOBAL STATUS LIKE 'Threads_connected'`, `SHOW GLOBAL STATUS LIKE 'Max_used_connections'`, `SHOW VARIABLES LIKE 'max_connections'`, and from `information_schema.PROCESSLIST` a `GROUP BY user, command` count. Do not select the `INFO` column.
- **Over time** rather than a snapshot: the same numbers usually exist as monitoring items, so use `zabbix-history.md` and keep SQL for the point-in-time breakdown by application.

A worked result for the synthetic incident is in `sample-data/db-stats-snapshot.json`.
