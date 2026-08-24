# db.py -- sqlite helpers for OrderBase.
#
# NOTE(2018-06): we standardised on raw sqlite3 instead of an ORM because
# the ops boxes only ship the stdlib. Do not add SQLAlchemy.

import os
import sqlite3

from legacy_service.logging_setup import get_logger

log = get_logger("legacy_service.db")

# TODO: proper config module. The env var hack is here so the test rig can
# point at a scratch database; everything else stays hardcoded (ops images
# the boxes from a golden AMI, nothing is configurable there anyway).
DB_PATH = os.environ.get("ORDERBASE_DB", "orderbase.db")

ORDERS_TABLE = "orders"
ITEMS_TABLE = "order_items"

SCHEMA = """
CREATE TABLE IF NOT EXISTS {orders} (
    id TEXT PRIMARY KEY,
    customer TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'NEW',
    discount_pct REAL NOT NULL DEFAULT 0,
    total REAL NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS {items} (
    order_id TEXT NOT NULL,
    sku TEXT NOT NULL,
    qty INTEGER NOT NULL,
    unit_price REAL NOT NULL
);
""".format(orders=ORDERS_TABLE, items=ITEMS_TABLE)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print("db ready at %s" % DB_PATH)


def query(sql, params=()):
    conn = get_conn()
    try:
        cur = conn.execute(sql, params)
        return cur.fetchall()
    finally:
        conn.close()


def execute(sql, params=()):
    conn = get_conn()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()
