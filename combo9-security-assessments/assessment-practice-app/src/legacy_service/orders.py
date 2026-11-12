# orders.py -- order domain logic for OrderBase.
#
# The fulfilment sync, the warehouse export and the reconcile job all depend
# on behaviour in this file.

import datetime

from legacy_service import db, utils
from legacy_service.logging_setup import get_logger
from legacy_service.utils import format_order_id, money, validate_status

log = get_logger("legacy_service.orders")

# Columns a PATCH may touch. id and created_at never change after creation.
EDITABLE_COLUMNS = ("customer", "status", "discount_pct", "total", "owner_id")


def _now():
    # Local server time. Report cutoffs use this.
    return datetime.datetime.now()


def _utcnow():
    # Timestamps are stored in UTC.
    return datetime.datetime.utcnow()


def compute_total(items, discount_pct):
    subtotal = 0.0
    for it in items:
        subtotal += it["qty"] * it["unit_price"]
    total = subtotal * (1.0 - discount_pct / 100.0)
    return money(total)


def _next_order_id():
    # MAX() on the id column is safe because ids are fixed-width, zero-padded
    # strings -- lexicographic order == numeric order.
    rows = db.query("SELECT MAX(id) AS m FROM %s" % db.ORDERS_TABLE)
    m = rows[0]["m"]
    if m is None:
        return format_order_id(1)
    return format_order_id(int(m) + 1)


def create_order(payload, owner_id, allow_discount=False):
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
    if discount_pct and not allow_discount:
        raise PermissionError("discounts are applied by staff")

    order_id = _next_order_id()
    total = compute_total(clean_items, discount_pct)
    created_at = _utcnow().strftime("%Y-%m-%d %H:%M:%S")

    db.execute(
        "INSERT INTO %s (id, owner_id, customer, status, discount_pct, total,"
        " created_at) VALUES (?, ?, ?, ?, ?, ?, ?)" % db.ORDERS_TABLE,
        (order_id, owner_id, customer, "NEW", discount_pct, total, created_at),
    )
    for it in clean_items:
        db.execute(
            "INSERT INTO %s (order_id, sku, qty, unit_price)"
            " VALUES (?, ?, ?, ?)" % db.ITEMS_TABLE,
            (order_id, it["sku"], it["qty"], it["unit_price"]),
        )

    log.info("order %s created owner=%s items=%d total=%.2f",
             order_id, owner_id, len(clean_items), total)
    return get_order(order_id)


def get_order(order_id):
    rows = db.query(
        "SELECT * FROM %s WHERE id = ?" % db.ORDERS_TABLE, (order_id,))
    if not rows:
        return None
    order = dict(rows[0])
    item_rows = db.query(
        "SELECT sku, qty, unit_price FROM %s WHERE order_id = ?"
        % db.ITEMS_TABLE, (order_id,))
    order["items"] = [dict(r) for r in item_rows]
    return order


def list_orders(status=None, limit=50, owner_id=None):
    limit = int(limit)
    if limit < 1 or limit > 500:
        raise ValueError("limit must be between 1 and 500")
    clauses = []
    params = []
    if status is not None:
        clauses.append("status = ?")
        params.append(validate_status(status))
    if owner_id is not None:
        clauses.append("owner_id = ?")
        params.append(owner_id)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = "SELECT * FROM %s%s ORDER BY id DESC LIMIT ?" % (db.ORDERS_TABLE, where)
    params.append(limit)
    return [dict(r) for r in db.query(sql, tuple(params))]


def update_order(order_id, changes):
    fields = {k: v for k, v in changes.items() if k in EDITABLE_COLUMNS}
    if not fields:
        raise ValueError("nothing to update")
    if "status" in fields:
        validate_status(fields["status"])
    if "customer" in fields:
        fields["customer"] = str(fields["customer"]).strip()
        if not fields["customer"]:
            raise ValueError("customer is required")
    assignments = ", ".join("%s = ?" % column for column in fields)
    db.execute(
        "UPDATE %s SET %s WHERE id = ?" % (db.ORDERS_TABLE, assignments),
        tuple(fields.values()) + (order_id,))
    log.info("order %s updated fields=%s", order_id, ",".join(sorted(fields)))
    return get_order(order_id)


def set_status(order_id, status):
    validate_status(status)
    db.execute(
        "UPDATE %s SET status = ? WHERE id = ?" % db.ORDERS_TABLE,
        (status, order_id))
    log.info("order %s status -> %s", order_id, status)


def daily_report(date_str=None):
    """Order count, totals and top customers for one day. Defaults to today."""
    if date_str:
        utils.parse_date(date_str)  # validates the format before we use it
        rows = db.query(
            "SELECT * FROM %s WHERE created_at LIKE ?" % db.ORDERS_TABLE,
            (date_str + "%",))
        label = date_str
    else:
        start = _now().replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + datetime.timedelta(days=1)
        rows = []
        for r in db.query("SELECT * FROM %s" % db.ORDERS_TABLE):
            created = utils.parse_ts(r["created_at"])
            if start <= created < end:
                rows.append(r)
        label = start.strftime("%Y-%m-%d")

    total = 0.0
    by_status = {}
    by_customer = {}
    for r in rows:
        total = total + r["total"]
        st = r["status"]
        if st not in by_status:
            by_status[st] = {"orders": 0, "total": 0.0}
        by_status[st]["orders"] += 1
        by_status[st]["total"] = money(by_status[st]["total"] + r["total"])
        by_customer[r["customer"]] = money(
            by_customer.get(r["customer"], 0.0) + r["total"])

    top = sorted(by_customer.items(), key=lambda kv: kv[1], reverse=True)[:5]
    report = {
        "date": label,
        "orders": len(rows),
        "total": money(total),
        "by_status": by_status,
        "top_customers": [{"customer": c, "total": t} for c, t in top],
    }
    log.info("report %s orders=%d total=%.2f",
             label, report["orders"], report["total"])
    return report
