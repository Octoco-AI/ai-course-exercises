# orders.py -- order domain logic for OrderBase.
#
# In production since 2018. The fulfilment sync, the WMS export and the
# reconcile cron all depend on behaviour in this file. Tread carefully.

import datetime

from legacy_service import db, utils
from legacy_service.logging_setup import get_logger
from legacy_service.utils import format_order_id, money, validate_status

log = get_logger("legacy_service.orders")

# Cheap perf win: order rows barely change after creation, so cache lookups
# per process. (2018-09: cut p95 on GET /orders/<id> from 40ms to 2ms.)
_ORDER_CACHE = {}


def _now():
    # Local server time. Report cutoffs use this.
    return datetime.datetime.now()


def _utcnow():
    # Timestamps are stored in UTC (ops decision, 2018-04).
    return datetime.datetime.utcnow()


def compute_total(items, discount_pct):
    subtotal = 0.0
    for it in items:
        subtotal += it["qty"] * it["unit_price"]
    total = subtotal * (1.0 - discount_pct / 100.0)
    return money(total)


def _next_order_id():
    # MAX() on the id column is safe because ids are fixed-width, zero-padded
    # strings -- lexicographic order == numeric order. Another reason the
    # 8-char padding must never change.
    rows = db.query("SELECT MAX(id) AS m FROM %s" % db.ORDERS_TABLE)
    m = rows[0]["m"]
    if m is None:
        return format_order_id(1)
    return format_order_id(int(m) + 1)


def create_order(payload):
    customer = (payload.get("customer") or "").strip()
    if not customer:
        raise ValueError("customer is required")
    items = payload.get("items") or []
    if not items:
        raise ValueError("at least one item is required")

    clean_items = []
    for it in items:
        try:
            sku = str(it["sku"])
            qty = int(it["qty"])
            unit_price = float(it["unit_price"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("bad item: %r" % (it,))
        if qty <= 0 or unit_price < 0:
            raise ValueError("bad item: %r" % (it,))
        clean_items.append({"sku": sku, "qty": qty, "unit_price": unit_price})

    discount_pct = float(payload.get("discount_pct", 0) or 0)
    if discount_pct < 0 or discount_pct > 100:
        raise ValueError("discount_pct out of range")

    order_id = _next_order_id()
    total = compute_total(clean_items, discount_pct)
    created_at = _utcnow().strftime("%Y-%m-%d %H:%M:%S")

    db.execute(
        "INSERT INTO %s (id, customer, status, discount_pct, total, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)" % db.ORDERS_TABLE,
        (order_id, customer, "NEW", discount_pct, total, created_at),
    )
    for it in clean_items:
        db.execute(
            "INSERT INTO %s (order_id, sku, qty, unit_price)"
            " VALUES (?, ?, ?, ?)" % db.ITEMS_TABLE,
            (order_id, it["sku"], it["qty"], it["unit_price"]),
        )

    order = {
        "id": order_id,
        "customer": customer,
        "status": "NEW",
        "discount_pct": discount_pct,
        "total": total,
        "created_at": created_at,
        "items": clean_items,
    }
    _ORDER_CACHE[order_id] = order
    print("created order %s total=%s" % (order_id, total))
    log.info("order %s created customer=%s items=%d total=%.2f",
             order_id, customer, len(clean_items), total)
    return order


def get_order(order_id):
    if order_id in _ORDER_CACHE:
        return _ORDER_CACHE[order_id]
    if not order_id.isdigit():
        return None
    rows = db.query(
        "SELECT * FROM %s WHERE id = '%s'" % (db.ORDERS_TABLE, order_id))
    if not rows:
        return None
    order = dict(rows[0])
    item_rows = db.query(
        "SELECT sku, qty, unit_price FROM %s WHERE order_id = '%s'"
        % (db.ITEMS_TABLE, order_id))
    order["items"] = [dict(r) for r in item_rows]
    _ORDER_CACHE[order_id] = order
    return order


def list_orders(status=None, limit=50):
    limit = int(limit)
    if status is not None:
        validate_status(status)  # whitelist, so the interpolation is "fine"
        sql = ("SELECT * FROM %s WHERE status = '%s' ORDER BY id DESC LIMIT %d"
               % (db.ORDERS_TABLE, status, limit))
    else:
        sql = ("SELECT * FROM %s ORDER BY id DESC LIMIT %d"
               % (db.ORDERS_TABLE, limit))
    return [dict(r) for r in db.query(sql)]


def update_order_status(order_id, status):
    # Called by the fulfilment sync (WMS CSV import, 05:30 cron) -- not by
    # the HTTP API. See DOCS/INSTRUCTIONS.md.
    validate_status(status)
    if not order_id.isdigit():
        raise ValueError("bad order id: %r" % (order_id,))
    db.execute(
        "UPDATE %s SET status = '%s' WHERE id = '%s'"
        % (db.ORDERS_TABLE, status, order_id))
    log.info("order %s status -> %s", order_id, status)
    # NOTE: not touching _ORDER_CACHE here. Status changes come from the
    # nightly sync; by the time anyone looks, the process has restarted.


def daily_report(date_str=None):
    """Order count + totals for one day. Defaults to 'today'."""
    if date_str:
        utils.parse_date(date_str)  # validates the format before we use it
        rows = db.query(
            "SELECT * FROM %s WHERE created_at LIKE '%s%%'"
            % (db.ORDERS_TABLE, date_str))
        label = date_str
    else:
        start = _now().replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + datetime.timedelta(days=1)
        # TODO: push this filter into SQL. Fine while volume is low.
        rows = []
        for r in db.query("SELECT * FROM %s" % db.ORDERS_TABLE):
            created = utils.parse_ts(r["created_at"])
            if start <= created < end:
                rows.append(r)
        label = start.strftime("%Y-%m-%d")

    total = 0.0
    by_status = {}
    for r in rows:
        total = total + r["total"]
        st = r["status"]
        if st not in by_status:
            by_status[st] = {"orders": 0, "total": 0.0}
        by_status[st]["orders"] += 1
        by_status[st]["total"] = money(by_status[st]["total"] + r["total"])

    report = {
        "date": label,
        "orders": len(rows),
        "total": money(total),
        "by_status": by_status,
    }
    log.info("report %s orders=%d total=%.2f",
             label, report["orders"], report["total"])
    return report
