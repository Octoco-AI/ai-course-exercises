import type { FastifyInstance } from "fastify";
import { afterEach, describe, expect, it } from "vitest";

import { buildApp } from "../src/app.js";
import { CANONICAL_CATEGORIES } from "../src/models.js";
import { FakeLlmClient, ThrowingLlmClient } from "./fakeLlmClient.js";
import type { LlmClient } from "../src/core.js";

/**
 * Layer 2 — API contract tests. Boots the real app in-process with a fake LLM.
 *
 * These check the shape of the HTTP contract, not the quality of the answer:
 * status codes, response fields, and — most importantly — that a contract
 * violation from the model becomes a 502 rather than a 500 or a crash.
 * Still no key, still free.
 *
 * `app.inject()` dispatches straight into the router without opening a socket,
 * so these run in milliseconds.
 */
describe("api", () => {
  let app: FastifyInstance | undefined;

  const appWith = (client: LlmClient) => {
    app = buildApp(client);
    return app;
  };

  afterEach(async () => {
    await app?.close();
    app = undefined;
  });

  it("GET /health returns ok", async () => {
    const response = await appWith(FakeLlmClient.returning("Other", 0.9)).inject({
      method: "GET",
      url: "/health",
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toEqual({ status: "ok" });
  });

  it("GET /categories returns the canonical list", async () => {
    const response = await appWith(FakeLlmClient.returning("Other", 0.9)).inject({
      method: "GET",
      url: "/categories",
    });

    expect(response.json().categories).toEqual([...CANONICAL_CATEGORIES]);
  });

  it("POST /categorise returns the model's answer", async () => {
    const response = await appWith(FakeLlmClient.returning("Food & Dining", 0.95)).inject({
      method: "POST",
      url: "/categorise",
      payload: { description: "Starbucks Coffee", amount: 5.45 },
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      category: "Food & Dining",
      used_fallback: false,
    });
  });

  it("POST /categorise: low confidence is still a 200", async () => {
    // The fallback is a successful response. The client needs to know the model
    // wasn't confident — not that the request failed.
    const response = await appWith(FakeLlmClient.returning("Travel", 0.2)).inject({
      method: "POST",
      url: "/categorise",
      payload: { description: "Something ambiguous", amount: 12 },
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({ category: "Other", used_fallback: true });
  });

  it("POST /categorise: a contract violation becomes 502", async () => {
    // Not a 500. The service is healthy; the model misbehaved. This distinction
    // is what lets the CE pipeline alert on model drift without drowning in
    // ordinary server errors.
    const response = await appWith(new FakeLlmClient("this is not json")).inject({
      method: "POST",
      url: "/categorise",
      payload: { description: "Starbucks", amount: 5.45 },
    });

    expect(response.statusCode).toBe(502);
  });

  it("POST /categorise: a missing API key becomes 500", async () => {
    const response = await appWith(
      new ThrowingLlmClient(new Error("GOOGLE_API_KEY is not set.")),
    ).inject({
      method: "POST",
      url: "/categorise",
      payload: { description: "Starbucks", amount: 5.45 },
    });

    expect(response.statusCode).toBe(500);
  });

  it("POST /categorise: rejects an empty description", async () => {
    const response = await appWith(FakeLlmClient.returning("Other", 0.9)).inject({
      method: "POST",
      url: "/categorise",
      payload: { description: "", amount: 5.45 },
    });

    expect(response.statusCode).toBe(400);
  });
});
