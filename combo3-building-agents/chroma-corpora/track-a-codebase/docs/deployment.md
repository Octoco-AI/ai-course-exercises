# Deployment

## Where

Fly.io, single-region (IAD). One primary application, one Postgres cluster, one managed Redis. All in the same region; we accept the single-region availability trade-off for now.

## How

`fly deploy` from the main branch after CI is green. CI uses a deploy token stored in `FLY_API_TOKEN` as a repo secret. The deploy command is:

```bash
fly deploy --remote-only
```

`--remote-only` means Fly builds the image — we do not run Docker locally.

## Rollouts

Fly's rolling strategy, one machine at a time. Default health check is `GET /health` returning 200 within 5 seconds. If a machine fails health, deploy rolls back automatically.

We do not use canary or blue/green. For this service that's acceptable; the traffic volume is low enough that "one machine at a time" rolls through in 30 seconds and the blast radius of a bad deploy is limited by the health check.

## Migrations

Alembic. Run automatically on every deploy via a release command in `fly.toml`:

```toml
[deploy]
release_command = "alembic upgrade head"
```

Migrations are backward-compatible by convention. Adding a column with a default, adding an index (concurrently), adding a table — all fine. Renaming or dropping a column is a two-step process: deploy the code that doesn't use it, THEN drop. We have a `lints` folder of Alembic ops that should never be used in a single migration; CI catches violations.

## Secrets

Set via `fly secrets set KEY=value`. Current secrets:

- `DATABASE_URL` — Postgres connection string. Set automatically by Fly's `fly pg attach`.
- `REDIS_URL` — Redis connection string.
- `SESSION_SIGNING_KEY` — HMAC key for session cookies.
- `HONEYCOMB_API_KEY` — OpenTelemetry export.
- `FLY_API_TOKEN` — used only in CI, never in the app.

Rotation: session signing key is rotated quarterly; this logs everyone out. Honeycomb key on-demand if we suspect exposure.

## Observability in production

Logs go to Fly's Loki. Traces go to Honeycomb. Metrics go to Fly's Prometheus. The ops dashboard linked from the team wiki pins the ~10 charts we actually look at:

- p50 / p95 / p99 latency per route
- Error rate per route
- DB pool utilisation
- Redis memory
- Sessions created per minute (login attempts)
- Todos completed per minute (primary business metric)

## Backups

Fly Postgres snapshots hourly, retained 14 days. Point-in-time restore within that window. We have tested the restore process twice; documented in `ops/runbooks/restore-from-backup.md`.

## Rollback

`fly releases` shows recent deploys; `fly releases rollback <id>` rolls the app back. Does NOT roll back migrations — if a bad migration went out, we must write a forward-fix migration. This is why the "backward-compatible migrations" rule exists.
