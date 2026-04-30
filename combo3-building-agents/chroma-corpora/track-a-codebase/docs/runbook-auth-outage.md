# Runbook: Authentication outage

## Symptom

Users can't log in. The `/auth/login` endpoint returns 500 or hangs.

## First checks

1. **Is the Fly app healthy?** `fly status` — all machines should be `running`. If some are `failed` or `crashed`, see runbook-app-outage.md.

2. **Is Redis reachable?** `fly ssh console` into any running machine and run:
   ```
   python -c "import redis, os; r = redis.from_url(os.environ['REDIS_URL']); print(r.ping())"
   ```
   `True` = Redis is fine. A timeout or connection error points at Redis.

3. **Is Postgres reachable?** Same shell:
   ```
   python -c "import sqlalchemy, os; e = sqlalchemy.create_engine(os.environ['DATABASE_URL']); print(e.connect().execute(sqlalchemy.text('SELECT 1')).scalar())"
   ```

## Scenario: Redis is down

The most common cause. Sessions live in Redis; if it's down, nothing authenticates.

- Check the Fly Redis dashboard. If it shows `failed`, restart from the dashboard.
- Restarts typically take 30–60 seconds. During that window, all logged-in users get a 401 on their next request.
- When Redis comes back, existing sessions are gone. Users need to re-log-in. Expected — we don't persist sessions beyond Redis.

## Scenario: Postgres slow or overloaded

Slow DB turns login timeouts (connection pool exhausted) into auth outage. If `fly postgres` shows high CPU or long-running queries:

- Check `pg_stat_activity` for runaway queries.
- Recently-deployed changes might have added an N+1 or missing index. Check the last few PRs.
- If nothing obvious, scale up: `fly postgres scale --vm-size shared-cpu-2x`. Temporary — we shouldn't leave it oversized.

## Scenario: bad deploy

If the outage started right after a deploy, check `fly releases`. Roll back:

```bash
fly releases rollback <previous-release-id>
```

Remember: this rolls back CODE only, not migrations. If the bad deploy ran a forward migration, the rolled-back code might not be compatible with the new schema. Check `ops/runbooks/restore-from-backup.md` if the migration is irreversible.

## Communication

- **Status page**: update `status.todomagic.com` within 5 minutes of confirming the outage. Template at `ops/status-templates/auth-outage.md`.
- **Support**: ping #support-escalations in Slack.
- **Post-incident**: schedule a postmortem if downtime > 10 minutes. Use `docs/templates/postmortem.md`.

## Prevention checklist

After every auth-related outage, review:

1. Did we have alerting on the right metric? (Login success rate is the leading indicator.)
2. Was the rollback path fast? Target is < 5 minutes from confirmed outage to rollback complete.
3. Was it something a failing test should have caught? If yes, write the test before closing the incident.
