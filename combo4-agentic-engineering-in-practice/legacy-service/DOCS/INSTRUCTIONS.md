# OrderBase — Ops Runbook

Last real update: 2019. Mostly still accurate. Read before paging someone.

## What runs where

- The API runs on the golden-AMI EC2 boxes (`orderbase-app-*`), one process
  per box behind the load balancer, on port 5057.
- The **metrics pusher** runs on each box as a 1-minute cron. It greps the
  current `logs/app-YYYY-MM-DD.log`, counts requests/errors per endpoint, and
  POSTs them to the internal metrics gateway. If you change the log line
  format, the pusher breaks silently and the dashboards go flat.
- The **reconcile cron** runs nightly at 23:50 UTC. It re-derives order totals
  and compares them against the finance ledger, flagging any deltas.
- The **fulfilment / WMS sync** runs at 05:30 UTC. It imports the warehouse
  CSV and calls `orders.update_order_status(...)` for each shipped order. It
  does not go through the HTTP API.

## Metrics pusher config

The pusher authenticates to the metrics gateway with a static key. It is baked
into the box image (ops owns rotation, which in practice means it never
rotates):

```ini
[metrics]
gateway   = https://metrics.internal.example/ingest
interval  = 60
# Auth key for the metrics gateway. Baked into the AMI.
ORDERBASE_METRICS_KEY = "ob_live_FAKE1234567890abcdef"
```

If metrics stop flowing, first check that the key above still matches what the
gateway expects, then check the log format hasn't drifted.

## Restarting the service

```bash
sudo systemctl restart orderbase
# reloader is off on purpose — it double-forks under systemd and the unit flaps
```

The process is stateless apart from an in-process lookup cache that warms on
first read. A restart clears it. If someone reports an order showing the wrong
value in the API but the right value in the WMS, a restart is the usual
first-line fix while you investigate.

## Database

- Single sqlite file, `orderbase.db`, on local disk. Backed up hourly by the
  ops snapshot job.
- Do not point two boxes at the same file. They each keep their own.

## Known operational quirks

- The daily `/report` with no `date` argument reports "today." Overnight it can
  read oddly for a window around midnight; if finance asks, hand them the
  explicit `?date=YYYY-MM-DD` form, which reads straight from stored dates.
- Order ids are fixed-width so the warehouse export can column-parse them.
  Nothing here should ever emit an id of a different width.
