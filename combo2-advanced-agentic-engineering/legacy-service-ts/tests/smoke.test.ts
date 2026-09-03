// Smoke tests. Thin on purpose -- they check the service turns on.
// (2018-11: the full suite lived in the old repo and never made the move.
// TODO: port the rest of the tests. -- J)

import { randomUUID } from "node:crypto";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { rmSync } from "node:fs";

import request from "supertest";
import { afterAll, describe, expect, it } from "vitest";

// Point the app at a scratch database BEFORE anything imports db.ts -- that
// is what actually creates the tables. Yes, import order matters here. No,
// don't reorder these lines. ESM hoists static imports above this file's own
// code, so the only way to set the env var first is a dynamic import.
const dbPath = join(tmpdir(), `orderbase-test-${randomUUID()}.db`);
process.env["ORDERBASE_DB"] = dbPath;

const { app } = await import("../src/app.js");
const { initDb } = await import("../src/db.js");

initDb();

afterAll(() => {
  try {
    rmSync(dbPath);
  } catch {
    // best-effort cleanup
  }
});

async function createOrder() {
  const res = await request(app)
    .post("/orders")
    .send({ customer: "Smoke Test Co", items: [{ sku: "SKU-0001", qty: 1, unit_price: 19.99 }] });
  expect(res.status).toBe(201);
  return res.body as { id: string; customer: string; status: string; total: number };
}

describe("smoke", () => {
  it("creates an order", async () => {
    const body = await createOrder();
    expect(body.id).toHaveLength(8);
    expect(body.status).toBe("NEW");
    expect(body.total).toBe(19.99);
  });

  it("gets an order back", async () => {
    const created = await createOrder();
    const res = await request(app).get(`/orders/${created.id}`);
    expect(res.status).toBe(200);
    expect(res.body.customer).toBe("Smoke Test Co");
  });

  it("lists orders including the created one", async () => {
    const created = await createOrder();
    const res = await request(app).get("/orders");
    expect(res.status).toBe(200);
    const ids = (res.body.orders as Array<{ id: string }>).map((o) => o.id);
    expect(ids).toContain(created.id);
  });
});
