#!/usr/bin/env python3
"""Seed OrderBase with deterministic sample data.

Creates ~30 orders spread over three days (2026-06-28 .. 2026-06-30) by going
through the real order-creation path (``orders.create_order``), then adjusting
each row's ``created_at`` and ``status`` to the target values. Running it twice
gives the same database every time.

Usage:
    python scripts/seed_data.py

Honours ``ORDERBASE_DB`` (defaults to ``orderbase.db`` in the working dir).
"""

import sys
from pathlib import Path

# Allow running as `python scripts/seed_data.py` without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from legacy_service import db, orders  # noqa: E402

DAYS = ["2026-06-28", "2026-06-29", "2026-06-30"]

CUSTOMERS = [
    "Acme Ltd", "Northwind Traders", "Globex", "Initech", "Umbrella Co",
    "Stark Supplies", "Wayne Retail", "Soylent Foods", "Hooli", "Vandelay",
]

# (sku, unit_price) catalogue. Prices chosen so that discounts land on a mix of
# clean and not-so-clean cent values.
CATALOGUE = [
    ("SKU-0001", 19.99),
    ("SKU-0002", 4.95),
    ("SKU-0003", 12.50),
    ("SKU-0004", 7.25),
    ("SKU-0005", 3.33),
    ("SKU-0006", 49.00),
    ("SKU-0007", 8.80),
    ("SKU-0008", 1.10),
    ("SKU-0009", 19.99),
]

DISCOUNT_CYCLE = [0, 0, 10, 5, 0, 15, 0, 7.5, 0, 10]
STATUS_CYCLE = ["NEW", "PAID", "SHIPPED", "PAID", "CANCELLED",
                "SHIPPED", "NEW", "PAID", "SHIPPED", "NEW"]

# A few orders are pinned so they line up with FAKE_SENTRY.md and the log
# fixtures (ids are assigned in creation order, starting at 00000001):
#   #7  -> SHIPPED, referenced by the stale-cache issue (ORDERBASE-9F2)
#   #21 -> 5 x SKU-0009 @ 19.99, 10% off -> reconcile mismatch (ORDERBASE-3A1)
PINNED = {
    7: {"status": "SHIPPED"},
    21: {"items": [("SKU-0009", 5)], "discount_pct": 10, "status": "SHIPPED"},
}

N_ORDERS = 30


def _build_payload(i):
    """Deterministically build the create_order payload for order i (1-based)."""
    customer = CUSTOMERS[(i - 1) % len(CUSTOMERS)]
    discount = DISCOUNT_CYCLE[(i - 1) % len(DISCOUNT_CYCLE)]

    # One-to-three line items, chosen deterministically from the catalogue.
    n_items = 1 + ((i - 1) % 3)
    items = []
    for j in range(n_items):
        sku, price = CATALOGUE[(i + j) % len(CATALOGUE)]
        qty = 1 + ((i + j) % 4)
        items.append({"sku": sku, "qty": qty, "unit_price": price})

    pin = PINNED.get(i, {})
    if "items" in pin:
        items = [{"sku": sku, "qty": qty, "unit_price": dict(CATALOGUE)[sku]}
                 for sku, qty in pin["items"]]
    if "discount_pct" in pin:
        discount = pin["discount_pct"]

    return {"customer": customer, "items": items, "discount_pct": discount}


def _target_meta(i):
    """The created_at timestamp and final status for order i (1-based)."""
    day = DAYS[(i - 1) // 10]
    # Spread orders through the working day, deterministically.
    hour = 8 + ((i * 3) % 11)          # 08:00 .. 18:00
    minute = (i * 7) % 60
    second = (i * 13) % 60
    created_at = "%s %02d:%02d:%02d" % (day, hour, minute, second)

    status = PINNED.get(i, {}).get("status") or STATUS_CYCLE[(i - 1) % len(STATUS_CYCLE)]
    return created_at, status


def seed():
    db.init_db()

    # Deterministic: clear existing rows so ids restart at 00000001.
    db.execute("DELETE FROM %s" % db.ORDERS_TABLE)
    db.execute("DELETE FROM %s" % db.ITEMS_TABLE)

    created_ids = []
    for i in range(1, N_ORDERS + 1):
        order = orders.create_order(_build_payload(i))
        created_at, status = _target_meta(i)
        db.execute(
            "UPDATE %s SET created_at = ?, status = ? WHERE id = ?"
            % db.ORDERS_TABLE,
            (created_at, status, order["id"]),
        )
        created_ids.append(order["id"])

    # Validate what we produced.
    rows = db.query("SELECT id, status, total, created_at FROM %s ORDER BY id"
                    % db.ORDERS_TABLE)
    assert len(rows) == N_ORDERS, "expected %d orders, got %d" % (N_ORDERS, len(rows))
    assert all(len(r["id"]) == 8 for r in rows), "found an id that is not 8 chars"

    print()
    print("Seeded %d orders into %s" % (len(rows), db.DB_PATH))
    for day in DAYS:
        day_rows = [r for r in rows if r["created_at"].startswith(day)]
        total = sum(r["total"] for r in day_rows)
        print("  %s: %2d orders, total %.2f" % (day, len(day_rows), total))
    print("  ids: %s .. %s" % (created_ids[0], created_ids[-1]))


if __name__ == "__main__":
    seed()
