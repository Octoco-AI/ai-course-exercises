// db.ts -- sqlite helpers for OrderBase.
//
// NOTE(2018-06): sqlite3, standardised on because the ops boxes only ship
// the golden-AMI runtime. 2024: ops moved us to the built-in node:sqlite
// when the native rebuilds of the old driver kept breaking the AMI bake --
// the one runtime dependency we have ever removed. Do NOT add Prisma,
// TypeORM, Knex, or any query builder.

import { DatabaseSync } from "node:sqlite";

// TODO: proper config module. The env var hack is here so the test rig can
// point at a scratch database; everything else stays hardcoded (ops images
// the boxes from a golden AMI, nothing is configurable there anyway).
export const DB_PATH = process.env["ORDERBASE_DB"] ?? "orderbase.db";

export const ORDERS_TABLE = "orders";
export const ITEMS_TABLE = "order_items";

const SCHEMA = `
CREATE TABLE IF NOT EXISTS ${ORDERS_TABLE} (
    id TEXT PRIMARY KEY,
    customer TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'NEW',
    discount_pct REAL NOT NULL DEFAULT 0,
    total REAL NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ${ITEMS_TABLE} (
    order_id TEXT NOT NULL,
    sku TEXT NOT NULL,
    qty INTEGER NOT NULL,
    unit_price REAL NOT NULL
);
`;

// One connection per process -- same lifetime as Python's implicit
// per-call sqlite3.connect(), just opened once instead of per query.
let conn: DatabaseSync | null = null;

function getConn(): DatabaseSync {
  conn ??= new DatabaseSync(DB_PATH);
  return conn;
}

export function initDb(): void {
  getConn().exec(SCHEMA);
  console.log(`db ready at ${DB_PATH}`);
}

export type Row = Record<string, unknown>; // TODO: type these properly. -- J, 2018

export function query(sql: string, ...params: unknown[]): Row[] {
  return getConn().prepare(sql).all(...(params as never[])) as Row[];
}

export function execute(sql: string, ...params: unknown[]): void {
  getConn().prepare(sql).run(...(params as never[]));
}
