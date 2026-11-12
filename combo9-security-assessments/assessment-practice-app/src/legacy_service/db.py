# db.py -- sqlite helpers for OrderBase.
#
# Raw sqlite3 rather than an ORM: the service is stdlib-first apart from
# Flask, and that decision still holds.

import sqlite3

from legacy_service import config
from legacy_service.logging_setup import get_logger
from legacy_service.utils import hash_token

log = get_logger("legacy_service.db")

DB_PATH = config.DB_PATH

ORDERS_TABLE = "orders"
ITEMS_TABLE = "order_items"
USERS_TABLE = "users"
KNOWN_TABLES = (ORDERS_TABLE, ITEMS_TABLE, USERS_TABLE)

SCHEMA = """
CREATE TABLE IF NOT EXISTS {users} (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    token_sha256 TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS {orders} (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
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
""".format(orders=ORDERS_TABLE, items=ITEMS_TABLE, users=USERS_TABLE)

# Local demo accounts, seeded into an empty database so the service is usable
# straight after install (see config.DEMO_USERS). The README lists them.
DEMO_USERS = (
    ("u-alice", "Alice", "customer", "alice-dev-token"),
    ("u-bob", "Bob", "customer", "bob-dev-token"),
    ("u-sam", "Sam (support)", "staff", "staff-dev-token"),
)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_count(table):
    if table not in KNOWN_TABLES:
        raise ValueError("unknown table: %r" % (table,))
    conn = get_conn()
    try:
        return conn.execute("SELECT COUNT(*) AS n FROM %s" % table).fetchone()["n"]
    finally:
        conn.close()


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    if config.DEMO_USERS and row_count(USERS_TABLE) == 0:
        for user_id, name, role, token in DEMO_USERS:
            execute(
                "INSERT INTO %s (id, name, role, token_sha256) VALUES (?, ?, ?, ?)"
                % USERS_TABLE,
                (user_id, name, role, hash_token(token)),
            )
        log.info("seeded %d demo users", len(DEMO_USERS))
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
