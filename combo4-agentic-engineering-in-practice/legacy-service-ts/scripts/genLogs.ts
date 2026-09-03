// genLogs.ts -- generate OrderBase log fixtures (TS port of gen_logs.py).
//
// Writes logs/app-2026-06-28.log .. logs/app-2026-06-30.log: a few hundred
// lines each of realistic, mixed-format noise (structured INFO request lines
// in the app's real log format, stray console.log-style lines with no
// prefix, the odd WARNING). A handful of production-bug signatures are
// seeded into the noise on specific days.
//
// Math.random() cannot be seeded, so the noise here uses a small hand-rolled
// PRNG (mulberry32) instead -- deterministic WITHIN this port, but it does
// not reproduce the same bytes as the Python or C# fixtures. That's fine:
// nothing asserts on the noise. The seeded signature lines below are
// hand-written and byte-identical to the other two ports modulo logger
// names -- those are what FAKE_SENTRY.md and the M27 symptom-to-code trace
// actually depend on.
//
// This script doubles as the "regenerate fixtures" microtooling example.
//
// Usage:
//   npx tsx scripts/genLogs.ts              # write into ./logs
//   npx tsx scripts/genLogs.ts --stdout      # print day 1 to stdout, write nothing

import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const LOG_DIR = join(REPO_ROOT, "logs");
const DAYS = ["2026-06-28", "2026-06-29", "2026-06-30"];

const APP = "legacy_service.app";
const ORD = "legacy_service.orders";

const CUSTOMERS = [
  "Acme Ltd", "Northwind Traders", "Globex", "Initech",
  "Umbrella Co", "Stark Supplies", "Wayne Retail", "Soylent Foods",
  "Hooli", "Vandelay",
];
const SKUS = [
  "SKU-0001", "SKU-0002", "SKU-0003", "SKU-0004", "SKU-0005",
  "SKU-0006", "SKU-0007", "SKU-0008", "SKU-0009",
];
const STATUSES = ["NEW", "PAID", "SHIPPED", "CANCELLED"];
const PRICES = [19.99, 4.95, 12.50, 7.25, 8.80];

// mulberry32 -- a tiny seedable PRNG. Not cryptographic, not Python's Mersenne
// Twister, not .NET's Random -- just deterministic within this file.
function mulberry32(seed: number): () => number {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

interface Rng {
  next(): number; // [0, 1)
  int(min: number, maxInclusive: number): number;
  choice<T>(items: readonly T[]): T;
}

function makeRng(seed: number): Rng {
  const gen = mulberry32(seed);
  return {
    next: () => gen(),
    int: (min, maxInclusive) => min + Math.floor(gen() * (maxInclusive - min + 1)),
    choice: (items) => items[Math.floor(gen() * items.length)] as (typeof items)[number],
  };
}

function money(x: number): number {
  const cents = x * 100;
  const whole = Math.floor(cents);
  return (cents - whole > 0.5 ? whole + 1 : whole) / 100;
}

function fmtTs(day: string, sec: number): string {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${day} ${pad(h)}:${pad(m)}:${pad(s)}`;
}

function logLine(day: string, sec: number, level: string, name: string, msg: string): string {
  return `${fmtTs(day, sec)} ${level} ${name} ${msg}`;
}

function orderId(n: number): string {
  return ("00000000" + n).slice(-8);
}

function randomEvent(rng: Rng, day: string, sec: number, counter: [number]): string[] {
  const roll = rng.next();
  const lines: string[] = [];

  if (roll < 0.42) {
    // GET /orders/<id>
    const oid = orderId(rng.int(1, Math.max(1, counter[0])));
    if (rng.next() < 0.06) {
      lines.push(logLine(day, sec, "INFO", APP, `GET /orders/${oid} 404`));
    } else {
      const status = rng.choice(STATUSES);
      lines.push(logLine(day, sec, "INFO", APP, `GET /orders/${oid} 200 status=${status}`));
    }
  } else if (roll < 0.60) {
    // GET /orders (list)
    const count = rng.int(1, 50);
    lines.push(logLine(day, sec, "INFO", APP, `GET /orders 200 count=${count}`));
  } else if (roll < 0.82) {
    // POST /orders -- emits the debug print, both log lines, and the stray
    // "created order" print, exactly as the code does.
    counter[0] += 1;
    const oid = orderId(counter[0]);
    const customer = rng.choice(CUSTOMERS);
    const nItems = rng.int(1, 3);
    const items = Array.from({ length: nItems }, () => ({
      sku: rng.choice(SKUS),
      qty: rng.int(1, 4),
      unit_price: rng.choice(PRICES),
    }));
    const total = money(items.reduce((sum, i) => sum + i.qty * i.unit_price, 0));
    const payload = { customer, items };
    lines.push(`DEBUG: POST /orders payload=${JSON.stringify(payload)}`); // stray
    lines.push(
      logLine(day, sec, "INFO", ORD, `order ${oid} created customer=${customer} items=${nItems} total=${total.toFixed(2)}`),
    );
    lines.push(`created order ${oid} total=${total}`); // stray
    lines.push(logLine(day, sec, "INFO", APP, `POST /orders 201 id=${oid} total=${total.toFixed(2)}`));
  } else if (roll < 0.92) {
    // GET /report
    const n = rng.int(4, 14);
    const total = money(rng.next() * (1600 - 300) + 300);
    lines.push(logLine(day, sec, "INFO", APP, `GET /report 200 date=${day} orders=${n} total=${total.toFixed(2)}`));
  } else {
    // An occasional rejected order (WARNING).
    const reasons = ["customer is required", "at least one item is required", "discount_pct out of range"];
    const reason = rng.choice(reasons);
    lines.push(logLine(day, sec, "WARNING", ORD, `rejected order: ${reason}`));
    lines.push(logLine(day, sec, "INFO", APP, `POST /orders 400 error="${reason}"`));
  }

  return lines;
}

function seededSignatures(day: string): Array<[number, string[]]> {
  const ev: Array<[number, string[]]> = [];

  if (day === "2026-06-28") {
    // Bug #1 flavour: reconcile finds a penny mismatch on a discounted order.
    ev.push([85805, [logLine(day, 85805, "INFO", "legacy_service.reconcile", "reconcile_day start date=2026-06-28")]]);
    ev.push([
      85808,
      [logLine(day, 85808, "WARNING", "legacy_service.reconcile", "total mismatch order=00000009 stored=32.62 recomputed=32.63 delta=0.01")],
    ]);
  }

  if (day === "2026-06-29") {
    // Bug #3: WMS sync sets SHIPPED at 05:31, but a later read serves NEW.
    ev.push([19800, ["db ready at orderbase.db"]]); // 05:30 sync boot
    ev.push([19870, [logLine(day, 19870, "INFO", ORD, "order 00000007 status -> SHIPPED")]]); // 05:31:10
    ev.push([33164, [logLine(day, 33164, "INFO", APP, "GET /orders/00000007 200 status=NEW")]]); // 09:12:44
    ev.push([
      33210,
      [logLine(day, 33210, "WARNING", "monitor", "order 00000007 shows NEW in API but SHIPPED in WMS (cache?)")],
    ]);
    // Bug #1 flavour again.
    ev.push([85805, [logLine(day, 85805, "INFO", "legacy_service.reconcile", "reconcile_day start date=2026-06-29")]]);
    ev.push([
      85809,
      [logLine(day, 85809, "WARNING", "legacy_service.reconcile", "total mismatch order=00000015 stored=9.40 recomputed=9.41 delta=0.01")],
    ]);
  }

  if (day === "2026-06-30") {
    // Bug #2: just after 00:00 UTC the no-date /report drops the day's rows.
    ev.push([192, [logLine(day, 192, "INFO", APP, "GET /report 200 date=2026-06-30 orders=0 total=0.00")]]); // 00:03:12
    ev.push([192, [logLine(day, 192, "WARNING", "monitor", "daily digest EMPTY for 2026-06-30 (expected>=8), retrying")]]);
    ev.push([1900, [logLine(day, 1900, "INFO", APP, "GET /report 200 date=2026-06-30 orders=0 total=0.00")]]); // 00:31:40
    ev.push([29525, [logLine(day, 29525, "INFO", APP, "GET /report?date=2026-06-30 200 orders=9 total=1043.71")]]); // 08:12:05
    // Bug #1: the reconcile mismatch that maps to FAKE_SENTRY ORDERBASE-3A1.
    ev.push([85805, [logLine(day, 85805, "INFO", "legacy_service.reconcile", "reconcile_day start date=2026-06-30")]]);
    ev.push([
      85808,
      [logLine(day, 85808, "WARNING", "legacy_service.reconcile", "total mismatch order=00000021 stored=89.95 recomputed=89.96 delta=0.01")],
    ]);
  }

  return ev;
}

function genDay(day: string, seed: number): string[] {
  const rng = makeRng(seed);
  const events: Array<[number, string[]]> = [
    // Boot banner (stray prints, no timestamp prefix).
    [4, ["db ready at orderbase.db"]],
    [5, ["OrderBase v1.4.2 listening on 0.0.0.0:5057 (debug=true)"]],
  ];

  const targetLines = rng.int(430, 540);
  const counter: [number] = [rng.int(30, 45)];
  let sec = rng.int(120, 400);
  let produced = 2;
  while (produced < targetLines && sec < 86200) {
    // Gaps are shorter during business hours, longer overnight.
    const hour = Math.floor(sec / 3600);
    const gap = hour >= 7 && hour <= 19 ? rng.int(15, 90) : rng.int(120, 600);
    sec += gap;
    const lines = randomEvent(rng, day, sec, counter);
    events.push([sec, lines]);
    produced += lines.length;
  }

  events.push(...seededSignatures(day));
  events.sort((a, b) => a[0] - b[0]);

  return events.flatMap(([, lines]) => lines);
}

// Every emitted line must match the frozen format (a hand-rolled test of the
// invariant the fixtures depend on -- the Python original lacks this).
const LINE_RE = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} (INFO|WARNING) \S+ .+$/;
function lineLooksValid(line: string): boolean {
  return (
    LINE_RE.test(line) ||
    line.startsWith("db ready") ||
    line.startsWith("OrderBase v") ||
    line.startsWith("created order") ||
    line.startsWith("DEBUG: ")
  );
}

function main(): void {
  if (process.argv.includes("--stdout")) {
    for (const line of genDay(DAYS[0]!, 42)) {
      console.log(line);
    }
    return;
  }

  mkdirSync(LOG_DIR, { recursive: true });
  DAYS.forEach((day, i) => {
    const lines = genDay(day, 42 + i);
    const invalid = lines.find((l) => !lineLooksValid(l));
    if (invalid !== undefined) {
      throw new Error(`generated a line that doesn't match the frozen format: ${invalid}`);
    }
    const path = join(LOG_DIR, `app-${day}.log`);
    writeFileSync(path, lines.join("\n") + "\n");
    console.log(`wrote ${path} (${lines.length} lines)`);
  });
}

main();
