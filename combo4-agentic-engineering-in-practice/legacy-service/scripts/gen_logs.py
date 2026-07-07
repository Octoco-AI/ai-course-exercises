#!/usr/bin/env python3
"""Generate OrderBase log fixtures.

Writes ``logs/app-2026-06-28.log`` .. ``logs/app-2026-06-30.log``: a few
hundred lines each of realistic, mixed-format noise (structured INFO request
lines in the app's real log format, stray ``print``-style lines with no
prefix, the odd WARNING). A handful of production-bug signatures are seeded
into the noise on specific days.

The output is fully deterministic (fixed RNG seeds), so regenerating and
committing produces a stable diff. This script doubles as the "regenerate
fixtures" microtooling example in Module 10 — keep it clean.

Usage:
    python scripts/gen_logs.py            # write into ./logs
    python scripts/gen_logs.py --stdout   # print day 1 to stdout, write nothing
"""

import argparse
import random
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
DAYS = ["2026-06-28", "2026-06-29", "2026-06-30"]

APP = "legacy_service.app"
ORD = "legacy_service.orders"

CUSTOMERS = ["Acme Ltd", "Northwind Traders", "Globex", "Initech",
             "Umbrella Co", "Stark Supplies", "Wayne Retail", "Soylent Foods",
             "Hooli", "Vandelay"]
SKUS = ["SKU-0001", "SKU-0002", "SKU-0003", "SKU-0004", "SKU-0005",
        "SKU-0006", "SKU-0007", "SKU-0008", "SKU-0009"]
STATUSES = ["NEW", "PAID", "SHIPPED", "CANCELLED"]


def fmt_ts(day, sec):
    return "%s %02d:%02d:%02d" % (day, sec // 3600, (sec % 3600) // 60, sec % 60)


def log_line(day, sec, level, name, msg):
    return "%s %s %s %s" % (fmt_ts(day, sec), level, name, msg)


def _order_id(n):
    return "%08d" % n


def _random_event(rng, day, sec, counter):
    """Return a list of already-formatted log lines for one request-ish event.

    ``counter`` is a mutable [int] used to hand out running order ids.
    """
    roll = rng.random()
    lines = []

    if roll < 0.42:
        # GET /orders/<id>
        oid = _order_id(rng.randint(1, max(1, counter[0])))
        if rng.random() < 0.06:
            lines.append(log_line(day, sec, "INFO", APP,
                                  "GET /orders/%s 404" % oid))
        else:
            status = rng.choice(STATUSES)
            lines.append(log_line(day, sec, "INFO", APP,
                                  "GET /orders/%s 200 status=%s" % (oid, status)))

    elif roll < 0.60:
        # GET /orders (list)
        count = rng.randint(1, 50)
        lines.append(log_line(day, sec, "INFO", APP,
                              "GET /orders 200 count=%d" % count))

    elif roll < 0.82:
        # POST /orders -- emits the debug print, both log lines, and the stray
        # "created order" print, exactly as the code does.
        counter[0] += 1
        oid = _order_id(counter[0])
        customer = rng.choice(CUSTOMERS)
        n_items = rng.randint(1, 3)
        items = [{"sku": rng.choice(SKUS), "qty": rng.randint(1, 4),
                  "unit_price": rng.choice([19.99, 4.95, 12.50, 7.25, 8.80])}
                 for _ in range(n_items)]
        total = round(sum(i["qty"] * i["unit_price"] for i in items), 2)
        payload = {"customer": customer, "items": items}
        lines.append("DEBUG: POST /orders payload=%r" % (payload,))       # stray
        lines.append(log_line(day, sec, "INFO", ORD,
                              "order %s created customer=%s items=%d total=%.2f"
                              % (oid, customer, n_items, total)))
        lines.append("created order %s total=%s" % (oid, total))           # stray
        lines.append(log_line(day, sec, "INFO", APP,
                              "POST /orders 201 id=%s total=%.2f" % (oid, total)))

    elif roll < 0.92:
        # GET /report
        n = rng.randint(4, 14)
        total = round(rng.uniform(300, 1600), 2)
        lines.append(log_line(day, sec, "INFO", APP,
                              "GET /report 200 date=%s orders=%d total=%.2f"
                              % (day, n, total)))

    else:
        # An occasional rejected order (WARNING).
        reason = rng.choice(["customer is required",
                             "at least one item is required",
                             "discount_pct out of range"])
        lines.append(log_line(day, sec, "WARNING", ORD, "rejected order: %s" % reason))
        lines.append(log_line(day, sec, "INFO", APP,
                              'POST /orders 400 error="%s"' % reason))

    return lines


def _seeded_signatures(day):
    """Bug signatures buried into specific days. Returns (sec, [lines]) tuples."""
    ev = []

    if day == "2026-06-28":
        # Bug #1 flavour: reconcile finds a penny mismatch on a discounted order.
        ev.append((85805, [log_line(day, 85805, "INFO", "legacy_service.reconcile",
                                    "reconcile_day start date=2026-06-28")]))
        ev.append((85808, [log_line(day, 85808, "WARNING", "legacy_service.reconcile",
                                    "total mismatch order=00000009 stored=32.62 recomputed=32.63 delta=0.01")]))

    if day == "2026-06-29":
        # Bug #3: WMS sync sets SHIPPED at 05:31, but a later read serves NEW.
        ev.append((19800, ["db ready at orderbase.db"]))                    # 05:30 sync boot
        ev.append((19870, [log_line(day, 19870, "INFO", ORD,
                                    "order 00000007 status -> SHIPPED")]))  # 05:31:10
        ev.append((33164, [log_line(day, 33164, "INFO", APP,
                                    "GET /orders/00000007 200 status=NEW")]))  # 09:12:44
        ev.append((33210, [log_line(day, 33210, "WARNING", "monitor",
                                    "order 00000007 shows NEW in API but SHIPPED in WMS (cache?)")]))
        # Bug #1 flavour again.
        ev.append((85805, [log_line(day, 85805, "INFO", "legacy_service.reconcile",
                                    "reconcile_day start date=2026-06-29")]))
        ev.append((85809, [log_line(day, 85809, "WARNING", "legacy_service.reconcile",
                                    "total mismatch order=00000015 stored=9.40 recomputed=9.41 delta=0.01")]))

    if day == "2026-06-30":
        # Bug #2: just after 00:00 UTC the no-date /report drops the day's rows.
        ev.append((192, [log_line(day, 192, "INFO", APP,
                                  "GET /report 200 date=2026-06-30 orders=0 total=0.00")]))  # 00:03:12
        ev.append((192, [log_line(day, 192, "WARNING", "monitor",
                                  "daily digest EMPTY for 2026-06-30 (expected>=8), retrying")]))
        ev.append((1900, [log_line(day, 1900, "INFO", APP,
                                   "GET /report 200 date=2026-06-30 orders=0 total=0.00")]))  # 00:31:40
        ev.append((29525, [log_line(day, 29525, "INFO", APP,
                                    "GET /report?date=2026-06-30 200 orders=9 total=1043.71")]))  # 08:12:05
        # Bug #1: the reconcile mismatch that maps to FAKE_SENTRY ORDERBASE-3A1.
        ev.append((85805, [log_line(day, 85805, "INFO", "legacy_service.reconcile",
                                    "reconcile_day start date=2026-06-30")]))
        ev.append((85808, [log_line(day, 85808, "WARNING", "legacy_service.reconcile",
                                    "total mismatch order=00000021 stored=89.95 recomputed=89.96 delta=0.01")]))

    return ev


def gen_day(day, seed):
    rng = random.Random(seed)
    events = []  # (sec, [lines])

    # Boot banner (stray prints, no timestamp prefix).
    events.append((4, ["db ready at orderbase.db"]))
    events.append((5, ["OrderBase v1.4.2 listening on 0.0.0.0:5057 (debug=True)"]))

    target_lines = rng.randint(430, 540)
    counter = [rng.randint(30, 45)]
    sec = rng.randint(120, 400)
    produced = 2
    while produced < target_lines and sec < 86200:
        # Gaps are shorter during business hours, longer overnight.
        hour = sec // 3600
        gap = rng.randint(15, 90) if 7 <= hour <= 19 else rng.randint(120, 600)
        sec += gap
        lines = _random_event(rng, day, sec, counter)
        events.append((sec, lines))
        produced += len(lines)

    events.extend(_seeded_signatures(day))
    events.sort(key=lambda e: e[0])

    out = []
    for _, lines in events:
        out.extend(lines)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stdout", action="store_true",
                        help="print the first day to stdout and write nothing")
    args = parser.parse_args()

    if args.stdout:
        print("\n".join(gen_day(DAYS[0], 42)))
        return

    LOG_DIR.mkdir(exist_ok=True)
    for i, day in enumerate(DAYS):
        lines = gen_day(day, 42 + i)
        path = LOG_DIR / ("app-%s.log" % day)
        path.write_text("\n".join(lines) + "\n")
        print("wrote %s (%d lines)" % (path, len(lines)))


if __name__ == "__main__":
    main()
