# OrderBase — exported issues

Three issues exported from our error tracker, lightly reformatted to Markdown.
No live links — treat these as the "one real production error you brought to
Day 2." Each one is real: it maps to code in `src/legacy_service/`. Your job
(Modules 8 and 11) is to trace each from the report to the line and confirm it.

---

## Issue ORDERBASE-3A1 — Order total does not reconcile with ledger (off by a cent)

- **Level:** error
- **First seen:** release `orderbase@1.3.0`
- **Last seen:** yesterday
- **Events:** 213 over 41 days · **Users affected:** finance (reconcile cron)
- **Frequency:** 3–8/day, spikes on discounted-promo days
- **Culprit:** `legacy_service.utils in money`

The nightly reconcile job re-derives each order total from its line items and
compares it to the stored total. It keeps flagging single-cent deltas on
orders that carry a discount. Always exactly ±0.01. Finance is annoyed.

```
LedgerMismatch: order 00000021 total does not reconcile:
    stored=89.95  recomputed=89.96  delta=0.01

Traceback (most recent call last):
  File "ops/reconcile_totals.py", line 66, in reconcile_day
    recomputed = compute_total(items, row["discount_pct"])
  File "src/legacy_service/orders.py", line 34, in compute_total
    return money(total)
  File "src/legacy_service/utils.py", line 17, in money
    return round(x, 2)
LedgerMismatch: stored=89.95 recomputed=89.96 delta=0.01
```

**Breadcrumbs**

```
14:07:41  http   POST /orders 201 id=00000021 total=89.95
14:07:41  order  order 00000021 created customer=Northwind items=1 total=89.95
14:07:41  data   items=[{"sku":"SKU-0009","qty":5,"unit_price":19.99}] discount_pct=10
23:50:04  cron   reconcile_day start date=2026-06-29
23:50:07  cron   mismatch order=00000021 stored=89.95 recomputed=89.96
```

**Grade:** easy. Reproducible on demand; the delta is deterministic per input.

---

## Issue ORDERBASE-7C4 — /report returns 0 orders for the current day overnight

- **Level:** warning
- **First seen:** release `orderbase@1.1.0`
- **Last seen:** this morning
- **Events:** 96 over 90+ days · **Users affected:** ops digest, finance
- **Frequency:** clusters every night between 00:00 and ~02:00 UTC, then stops
- **Culprit:** `legacy_service.orders in daily_report`

The ops daily-digest job calls `/report` with no `date` (i.e. "today"). For a
window after midnight UTC it comes back with `orders=0, total=0.00`, even
though orders exist for that day. Asking for the same day explicitly
(`?date=YYYY-MM-DD`) returns the real numbers. By morning the no-date form is
correct again. It has done this "forever."

```
ReportEmpty: daily digest got 0 orders for 2026-06-30 (expected >= 8)

Traceback (most recent call last):
  File "ops/daily_digest.py", line 40, in send_digest
    rep = daily_report()
  File "src/legacy_service/orders.py", line 157, in daily_report
    start = _now().replace(hour=0, minute=0, second=0, microsecond=0)
  File "src/legacy_service/orders.py", line 163, in daily_report
    if start <= created < end:
ReportEmpty: window=[2026-06-29 00:00, 2026-06-30 00:00) dropped all 2026-06-30 rows
```

**Breadcrumbs**

```
2026-06-30 00:03:12  http   GET /report 200 date=2026-06-30 orders=0 total=0.00
2026-06-30 00:03:12  ops    daily digest EMPTY, will retry
2026-06-30 00:31:40  http   GET /report 200 date=2026-06-30 orders=0 total=0.00
2026-06-30 08:12:05  http   GET /report?date=2026-06-30 200 orders=9 total=1043.71
2026-06-30 08:12:05  ops    server TZ != UTC (offset -03:00)
```

**Grade:** medium. Time-of-day dependent; only reproduces near the UTC day
boundary or with a non-UTC server clock.

---

## Issue ORDERBASE-9F2 — GET /orders/<id> serves stale status after WMS sync

- **Level:** warning
- **First seen:** release `orderbase@1.2.1`
- **Last seen:** last week
- **Events:** 11 over 60 days · **Users affected:** customer support, 1 buyer
- **Frequency:** rare, 1–3/week; only on boxes with long uptime
- **Culprit:** `legacy_service.orders in get_order`

Support reports orders that show `NEW` in the API but `SHIPPED` in the
warehouse system. The 05:30 fulfilment sync updates the DB row correctly, but
the API keeps returning the old value. A service restart "fixes" it, then it
recurs days later. Only ever seen on app boxes that haven't been restarted in
a while.

```
StaleRead: order 00000007 API status=NEW but DB status=SHIPPED (process uptime 3d)

Traceback (most recent call last):
  File "ops/consistency_probe.py", line 52, in check_order
    served = get_order(order_id)
  File "src/legacy_service/orders.py", line 106, in get_order
    return _ORDER_CACHE[order_id]
StaleRead: served status=NEW, db status=SHIPPED for id=00000007
```

**Breadcrumbs**

```
2026-06-29 05:31:10  sync   order 00000007 status -> SHIPPED
2026-06-29 09:12:44  http   GET /orders/00000007 200 status=NEW
2026-06-29 09:13:02  support ticket #4471 "app says NEW, warehouse says shipped"
2026-06-29 09:40:00  ops    restarted orderbase on box app-02, ticket resolved
```

**Grade:** subtle. Requires a long-lived process, an out-of-band DB write, and
a read that was cached before the write. Doesn't reproduce on a fresh process.
