// orders.ts -- order domain logic for OrderBase.
//
// In production since 2018. The fulfilment sync, the WMS export and the
// reconcile cron all depend on behaviour in this file. Tread carefully.

import * as db from "./db.js";
import { getLogger } from "./loggingSetup.js";
import { formatOrderId, money, parseDate, parseTs, validateStatus } from "./utils.js";

const log = getLogger("legacy_service.orders");

export interface OrderItem {
  sku: string;
  qty: number;
  unit_price: number;
}

// The order itself. A plain mutable object, not a frozen/readonly type --
// see the comment on the cache below. A `readonly`-everywhere interface plus
// object-spread updates would quietly fix the cache's reference-bleed bug.
export interface Order {
  id: string;
  customer: string;
  status: string;
  discount_pct: number;
  total: number;
  created_at: string;
  items: OrderItem[];
}

export interface StatusBucket {
  orders: number;
  total: number;
}

export interface DailyReportResult {
  date: string;
  orders: number;
  total: number;
  by_status: Record<string, StatusBucket>;
}

// Cheap perf win: order rows barely change after creation, so cache lookups
// per process. (2018-09: cut p95 on GET /orders/<id> from 40ms to 2ms.)
const _orderCache = new Map<string, Order>();

// Hung off an object so the 2019 report tests could pin the clock. Nothing
// in production ever reassigns these.
export const clock = {
  now: (): Date => new Date(), // local server time. Report cutoffs use this.
  utcnow: (): Date => new Date(), // timestamps are stored in UTC (ops decision, 2018-04)
};

export function computeTotal(items: OrderItem[], discountPct: number): number {
  let subtotal = 0;
  for (const it of items) {
    subtotal += it.qty * it.unit_price;
  }
  const total = subtotal * (1 - discountPct / 100);
  return money(total);
}

function nextOrderId(): string {
  // MAX() is safe because ids are fixed-width, zero-padded strings --
  // lexicographic order == numeric order. Another reason the 8-char padding
  // must never change.
  const rows = db.query(`SELECT MAX(id) AS m FROM ${db.ORDERS_TABLE}`);
  const m = rows[0]?.["m"] as string | null | undefined;
  if (m === null || m === undefined) {
    return formatOrderId(1);
  }
  return formatOrderId(Number.parseInt(m, 10) + 1);
}

function utcTimestamp(d: Date): string {
  return d.toISOString().slice(0, 19).replace("T", " ");
}

export function createOrder(payload: unknown): Order {
  const body = (payload ?? {}) as Record<string, unknown>;

  const customer = typeof body["customer"] === "string" ? body["customer"].trim() : "";
  if (customer.length === 0) {
    throw new Error("customer is required");
  }

  const rawItems = body["items"];
  if (!Array.isArray(rawItems) || rawItems.length === 0) {
    throw new Error("at least one item is required");
  }

  const cleanItems: OrderItem[] = [];
  for (const it of rawItems) {
    const sku = it?.["sku"];
    const qty = Number(it?.["qty"]);
    const unitPrice = Number(it?.["unit_price"]);
    if (typeof sku !== "string" && typeof sku !== "number") {
      throw new Error(`bad item: ${JSON.stringify(it)}`);
    }
    if (!Number.isFinite(qty) || !Number.isFinite(unitPrice)) {
      throw new Error(`bad item: ${JSON.stringify(it)}`);
    }
    if (qty <= 0 || unitPrice < 0) {
      throw new Error(`bad item: ${JSON.stringify(it)}`);
    }
    cleanItems.push({ sku: String(sku), qty, unit_price: unitPrice });
  }

  let discountPct = 0;
  if (body["discount_pct"] !== undefined && body["discount_pct"] !== null) {
    discountPct = Number(body["discount_pct"]);
    if (!Number.isFinite(discountPct)) {
      throw new Error("discount_pct out of range");
    }
  }
  if (discountPct < 0 || discountPct > 100) {
    throw new Error("discount_pct out of range");
  }

  const orderId = nextOrderId();
  const total = computeTotal(cleanItems, discountPct);
  const createdAt = utcTimestamp(clock.utcnow());

  db.execute(
    `INSERT INTO ${db.ORDERS_TABLE} (id, customer, status, discount_pct, total, created_at)` +
      " VALUES (?, ?, ?, ?, ?, ?)",
    orderId,
    customer,
    "NEW",
    discountPct,
    total,
    createdAt,
  );
  for (const it of cleanItems) {
    db.execute(
      `INSERT INTO ${db.ITEMS_TABLE} (order_id, sku, qty, unit_price) VALUES (?, ?, ?, ?)`,
      orderId,
      it.sku,
      it.qty,
      it.unit_price,
    );
  }

  const order: Order = {
    id: orderId,
    customer,
    status: "NEW",
    discount_pct: discountPct,
    total,
    created_at: createdAt,
    items: cleanItems,
  };
  _orderCache.set(orderId, order);
  console.log(`created order ${orderId} total=${total}`);
  log.info("order {} created customer={} items={} total={}", orderId, customer, cleanItems.length, total.toFixed(2));
  return order;
}

function isDigits(s: string): boolean {
  return s.length > 0 && /^\d+$/.test(s);
}

export function getOrder(orderId: string): Order | null {
  const cached = _orderCache.get(orderId);
  if (cached !== undefined) {
    return cached; // the cached object itself
  }
  if (!isDigits(orderId)) {
    return null;
  }
  const rows = db.query(`SELECT * FROM ${db.ORDERS_TABLE} WHERE id = '${orderId}'`);
  if (rows.length === 0) {
    return null;
  }
  const row = rows[0]!;
  const itemRows = db.query(
    `SELECT sku, qty, unit_price FROM ${db.ITEMS_TABLE} WHERE order_id = '${orderId}'`,
  );
  const order: Order = {
    id: row["id"] as string,
    customer: row["customer"] as string,
    status: row["status"] as string,
    discount_pct: row["discount_pct"] as number,
    total: row["total"] as number,
    created_at: row["created_at"] as string,
    items: itemRows.map((r) => ({
      sku: r["sku"] as string,
      qty: r["qty"] as number,
      unit_price: r["unit_price"] as number,
    })),
  };
  _orderCache.set(orderId, order);
  return order;
}

export function listOrders(status: string | undefined, limit: number): Order[] {
  let rows: db.Row[];
  if (status !== undefined) {
    validateStatus(status); // whitelist, so the interpolation is "fine"
    rows = db.query(
      `SELECT * FROM ${db.ORDERS_TABLE} WHERE status = '${status}' ORDER BY id DESC LIMIT ${limit}`,
    );
  } else {
    rows = db.query(`SELECT * FROM ${db.ORDERS_TABLE} ORDER BY id DESC LIMIT ${limit}`);
  }
  return rows.map((r) => ({
    id: r["id"] as string,
    customer: r["customer"] as string,
    status: r["status"] as string,
    discount_pct: r["discount_pct"] as number,
    total: r["total"] as number,
    created_at: r["created_at"] as string,
    items: [],
  }));
}

export function updateOrderStatus(orderId: string, status: string): void {
  // Called by the fulfilment sync (WMS CSV import, 05:30 cron) -- not by the
  // HTTP API. See DOCS/INSTRUCTIONS.md.
  validateStatus(status);
  if (!isDigits(orderId)) {
    throw new Error(`bad order id: ${orderId}`);
  }
  db.execute(`UPDATE ${db.ORDERS_TABLE} SET status = '${status}' WHERE id = '${orderId}'`);
  log.info("order {} status -> {}", orderId, status);
  // NOTE: not touching _orderCache here. Status changes come from the
  // nightly sync; by the time anyone looks, the process has restarted.
}

export function dailyReport(dateStr?: string): DailyReportResult {
  let rows: db.Row[];
  let label: string;
  if (dateStr !== undefined) {
    parseDate(dateStr); // validates the format before we use it
    rows = db.query(`SELECT * FROM ${db.ORDERS_TABLE} WHERE created_at LIKE '${dateStr}%'`);
    label = dateStr;
  } else {
    const n = clock.now();
    const start = new Date(n.getFullYear(), n.getMonth(), n.getDate()); // local midnight
    const end = new Date(start.getTime() + 24 * 60 * 60 * 1000);
    // TODO: push this filter into SQL. Fine while volume is low.
    rows = [];
    for (const r of db.query(`SELECT * FROM ${db.ORDERS_TABLE}`)) {
      const created = parseTs(r["created_at"] as string);
      if (start <= created && created < end) {
        rows.push(r);
      }
    }
    label = `${start.getFullYear()}-${String(start.getMonth() + 1).padStart(2, "0")}-${String(start.getDate()).padStart(2, "0")}`;
  }

  let total = 0;
  const byStatus: Record<string, StatusBucket> = {};
  for (const r of rows) {
    const rowTotal = r["total"] as number;
    total += rowTotal;
    const st = r["status"] as string;
    const bucket = (byStatus[st] ??= { orders: 0, total: 0 });
    bucket.orders += 1;
    bucket.total = money(bucket.total + rowTotal);
  }

  const report: DailyReportResult = {
    date: label,
    orders: rows.length,
    total: money(total),
    by_status: byStatus,
  };
  log.info("report {} orders={} total={}", label, report.orders, report.total.toFixed(2));
  return report;
}
