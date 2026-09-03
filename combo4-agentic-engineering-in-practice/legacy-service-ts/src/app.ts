// app.ts -- OrderBase HTTP API.
//
// Four endpoints. In production since 2018. If you are reading this because
// something broke: logs are in logs/, the reconcile cron is in the ops repo,
// and DOCS/INSTRUCTIONS.md is roughly current (last real update 2019).
//
// `app` is a module-level singleton, not a buildApp() factory -- that is the
// deliberate, "2018 Express app" shape. It also means importing this module
// for tests never boots the logger or the db; see server.ts for the split
// and why it matters.

import express, { type NextFunction, type Request, type Response } from "express";

import { getLogger } from "./loggingSetup.js";
import { createOrder, dailyReport, getOrder, listOrders } from "./orders.js";

export const APP_VERSION = "1.4.2";

// Ops images the boxes from a golden AMI; nothing below is meant to be
// configurable. The port was picked in 2018 to dodge the office proxy.
export const HOST = "0.0.0.0";
export const PORT = 5057;
export const DEBUG = true; // left on after the 2019 checkout incident. Do not ask.

const log = getLogger("legacy_service.app");

export const app = express();
app.use(express.json());

// Malformed JSON body -> the same 400 shape Flask's request.get_json(silent=True)
// gives us. Must sit directly after express.json() so it only catches parse
// errors from that middleware, not errors from the route handlers below.
app.use((err: unknown, _req: Request, res: Response, next: NextFunction) => {
  if (err instanceof SyntaxError && "body" in (err as unknown as Record<string, unknown>)) {
    res.status(400).json({ error: "body must be JSON" });
    return;
  }
  next(err);
});

app.post("/orders", (req: Request, res: Response) => {
  if (DEBUG) {
    console.log(`DEBUG: POST /orders payload=${JSON.stringify(req.body)}`);
  }
  let order;
  try {
    order = createOrder(req.body);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    log.warning("rejected order: {}", message);
    res.status(400).json({ error: message });
    return;
  }
  log.info("POST /orders 201 id={} total={}", order.id, order.total.toFixed(2));
  res.status(201).json(order);
});

app.get("/orders/:orderId", (req: Request, res: Response) => {
  let orderId = (req.params["orderId"] as string | undefined) ?? "";
  // Accept bare numeric ids ("42") as a convenience and pad them.
  // (Same rule as utils.formatOrderId -- keep the two in sync.)
  if (orderId.length > 0 && orderId.length < 8 && /^\d+$/.test(orderId)) {
    orderId = orderId.padStart(8, "0");
  }
  const order = getOrder(orderId);
  if (order === null) {
    log.info("GET /orders/{} 404", orderId);
    res.status(404).json({ error: `order ${orderId} not found` });
    return;
  }
  log.info("GET /orders/{} 200 status={}", orderId, order.status);
  res.json(order);
});

app.get("/orders", (req: Request, res: Response) => {
  const status = typeof req.query["status"] === "string" ? req.query["status"] : undefined;
  const limitRaw = typeof req.query["limit"] === "string" ? req.query["limit"] : "50";
  const limit = Number.parseInt(limitRaw, 10);
  if (!Number.isFinite(limit) || String(limit) !== limitRaw.trim()) {
    res.status(400).json({ error: `invalid limit: '${limitRaw}'` });
    return;
  }

  let result;
  try {
    result = listOrders(status, limit);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    res.status(400).json({ error: message });
    return;
  }
  log.info("GET /orders 200 count={}", result.length);
  res.json({ orders: result, count: result.length });
});

app.get("/report", (req: Request, res: Response) => {
  const date = typeof req.query["date"] === "string" ? req.query["date"] : undefined;
  let report;
  try {
    report = dailyReport(date);
  } catch {
    res.status(400).json({ error: "date must be YYYY-MM-DD" });
    return;
  }
  log.info("GET /report 200 date={} orders={} total={}", report.date, report.orders, report.total.toFixed(2));
  res.json(report);
});

// NOTE: monitoring hits GET /orders?limit=1 as a liveness probe because we
// never got around to a proper health endpoint.
