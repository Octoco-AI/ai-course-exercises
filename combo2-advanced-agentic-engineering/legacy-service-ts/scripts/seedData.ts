// seedData.ts -- seed OrderBase with deterministic sample data (TS port of
// seed_data.py).
//
// Creates ~30 orders spread over three days (2026-06-28 .. 2026-06-30) by
// going through the real order-creation path (createOrder), then adjusting
// each row's created_at and status to the target values. Running it twice
// gives the same database every time -- and, since it drives the real
// computeTotal, the same 30 totals as Python except order #16, where this
// port's half-down money() rounding diverges by one cent (see FACILITATOR.md
// -- the C# port is exact on all 30, this one is exact on 29).
//
// Usage:
//   npx tsx scripts/seedData.ts
//
// Honours ORDERBASE_DB (defaults to orderbase.db in the working dir).

import * as db from "../src/db.js";
import { createOrder } from "../src/orders.js";

const DAYS = ["2026-06-28", "2026-06-29", "2026-06-30"];

const CUSTOMERS = [
  "Acme Ltd", "Northwind Traders", "Globex", "Initech", "Umbrella Co",
  "Stark Supplies", "Wayne Retail", "Soylent Foods", "Hooli", "Vandelay",
];

// (sku, unit_price) catalogue. Prices chosen so that discounts land on a mix
// of clean and not-so-clean cent values.
const CATALOGUE: Array<[string, number]> = [
  ["SKU-0001", 19.99], ["SKU-0002", 4.95], ["SKU-0003", 12.50],
  ["SKU-0004", 7.25], ["SKU-0005", 3.33], ["SKU-0006", 49.00],
  ["SKU-0007", 8.80], ["SKU-0008", 1.10], ["SKU-0009", 19.99],
];
const PRICE_BY_SKU = new Map(CATALOGUE);

const DISCOUNT_CYCLE = [0, 0, 10, 5, 0, 15, 0, 7.5, 0, 10];
const STATUS_CYCLE = ["NEW", "PAID", "SHIPPED", "PAID", "CANCELLED", "SHIPPED", "NEW", "PAID", "SHIPPED", "NEW"];

// A few orders are pinned so they line up with FAKE_SENTRY.md and the log
// fixtures (ids are assigned in creation order, starting at 00000001):
//   #7  -> SHIPPED, referenced by the stale-cache issue (ORDERBASE-9F2)
//   #21 -> 5 x SKU-0009 @ 19.99, 10% off -> reconcile mismatch (ORDERBASE-3A1)
const PINNED: Record<number, { items?: Array<[string, number]>; discountPct?: number; status?: string }> = {
  7: { status: "SHIPPED" },
  21: { items: [["SKU-0009", 5]], discountPct: 10, status: "SHIPPED" },
};

const N_ORDERS = 30;

function buildPayload(i: number) {
  const customer = CUSTOMERS[(i - 1) % CUSTOMERS.length];
  let discount = DISCOUNT_CYCLE[(i - 1) % DISCOUNT_CYCLE.length]!;

  // One-to-three line items, chosen deterministically from the catalogue.
  const nItems = 1 + ((i - 1) % 3);
  let items: Array<{ sku: string; qty: number; unit_price: number }> = [];
  for (let j = 0; j < nItems; j++) {
    const [sku, price] = CATALOGUE[(i + j) % CATALOGUE.length]!;
    const qty = 1 + ((i + j) % 4);
    items.push({ sku, qty, unit_price: price });
  }

  const pin = PINNED[i];
  if (pin?.items) {
    items = pin.items.map(([sku, qty]) => ({ sku, qty, unit_price: PRICE_BY_SKU.get(sku)! }));
  }
  if (pin?.discountPct !== undefined) {
    discount = pin.discountPct;
  }

  return { customer, items, discount_pct: discount };
}

function targetMeta(i: number): { createdAt: string; status: string } {
  const day = DAYS[Math.floor((i - 1) / 10)]!;
  // Spread orders through the working day, deterministically.
  const hour = 8 + ((i * 3) % 11);
  const minute = (i * 7) % 60;
  const second = (i * 13) % 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  const createdAt = `${day} ${pad(hour)}:${pad(minute)}:${pad(second)}`;

  const status = PINNED[i]?.status ?? STATUS_CYCLE[(i - 1) % STATUS_CYCLE.length]!;
  return { createdAt, status };
}

function seed(): void {
  db.initDb();

  // Deterministic: clear existing rows so ids restart at 00000001.
  db.execute(`DELETE FROM ${db.ORDERS_TABLE}`);
  db.execute(`DELETE FROM ${db.ITEMS_TABLE}`);

  const createdIds: string[] = [];
  for (let i = 1; i <= N_ORDERS; i++) {
    const order = createOrder(buildPayload(i));
    const { createdAt, status } = targetMeta(i);
    db.execute(`UPDATE ${db.ORDERS_TABLE} SET created_at = ?, status = ? WHERE id = ?`, createdAt, status, order.id);
    createdIds.push(order.id);
  }

  // Validate what we produced. (Assertions the Python original lacks -- this
  // is the "regenerate fixtures WITH validation" chore.)
  const rows = db.query(`SELECT id, status, total, created_at FROM ${db.ORDERS_TABLE} ORDER BY id`);
  if (rows.length !== N_ORDERS) {
    throw new Error(`expected ${N_ORDERS} orders, got ${rows.length}`);
  }
  if (rows.some((r) => (r["id"] as string).length !== 8)) {
    throw new Error("found an id that is not 8 chars");
  }
  const order21 = rows.find((r) => r["id"] === "00000021")!;
  if (order21["total"] !== 89.95) {
    throw new Error(`order #21 should total 89.95, got ${order21["total"]}`);
  }
  const order7 = rows.find((r) => r["id"] === "00000007")!;
  if (order7["status"] !== "SHIPPED") {
    throw new Error(`order #7 should be SHIPPED, got ${order7["status"]}`);
  }

  console.log();
  console.log(`Seeded ${rows.length} orders into ${db.DB_PATH}`);
  for (const day of DAYS) {
    const dayRows = rows.filter((r) => (r["created_at"] as string).startsWith(day));
    const total = dayRows.reduce((sum, r) => sum + (r["total"] as number), 0);
    console.log(`  ${day}: ${String(dayRows.length).padStart(2)} orders, total ${total.toFixed(2)}`);
  }
  console.log(`  ids: ${createdIds[0]} .. ${createdIds[createdIds.length - 1]}`);
}

seed();
