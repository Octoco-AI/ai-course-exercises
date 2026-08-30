import { describe, expect, it } from "vitest";

import {
  applyConfidenceThreshold,
  buildPrompt,
  buildSystemPrompt,
  categorise,
  parseResponse,
} from "../src/core.js";
import { CANONICAL_CATEGORIES, ContractViolationError } from "../src/models.js";
import { FakeLlmClient } from "./fakeLlmClient.js";

/**
 * Layer 1 — unit tests over the deterministic parts. No LLM, no key, no cost.
 *
 * This is the layer most teams skip when they build an AI feature, on the
 * grounds that "it's all AI, you can't test it". Look how much of this file
 * tests ordinary code with exact assertions. That is the point of pulling
 * buildPrompt, parseResponse and applyConfidenceThreshold apart in the first
 * place.
 */
describe("buildPrompt", () => {
  it("formats description and amount", () => {
    expect(buildPrompt("Whole Foods Market", 78.23)).toBe(
      'Transaction: "Whole Foods Market"\nAmount: 78.23',
    );
  });

  it("always uses two decimal places", () => {
    expect(buildPrompt("Coffee", 5)).toContain("Amount: 5.00");
    expect(buildPrompt("Refund", -20)).toContain("Amount: -20.00");
  });
});

describe("buildSystemPrompt", () => {
  it("lists every canonical category", () => {
    const prompt = buildSystemPrompt();
    for (const category of CANONICAL_CATEGORIES) {
      expect(prompt).toContain(`  - ${category}`);
    }
  });
});

describe("parseResponse", () => {
  it("accepts valid JSON", () => {
    const parsed = parseResponse('{"category": "Food & Dining", "confidence": 0.95}');

    expect(parsed.category).toBe("Food & Dining");
    expect(parsed.confidence).toBeCloseTo(0.95);
  });

  it("rejects malformed JSON", () => {
    expect(() => parseResponse("not json at all")).toThrow(ContractViolationError);
    expect(() => parseResponse("not json at all")).toThrow(/not valid JSON/);
  });

  it("rejects a non-object", () => {
    expect(() => parseResponse("[1, 2, 3]")).toThrow(/must be a JSON object/);
  });

  it("rejects missing fields", () => {
    expect(() => parseResponse('{"category": "Food & Dining"}')).toThrow(ContractViolationError);
    expect(() => parseResponse('{"confidence": 0.9}')).toThrow(ContractViolationError);
  });

  it("rejects an unknown category", () => {
    // The model inventing a category is the most common contract violation in
    // practice, and the easiest to miss without this assertion.
    expect(() => parseResponse('{"category": "Snacks", "confidence": 0.9}')).toThrow(
      /unknown category/,
    );
  });

  it.each([-0.1, 1.5])("rejects out-of-range confidence: %s", (confidence) => {
    expect(() => parseResponse(`{"category": "Other", "confidence": ${confidence}}`)).toThrow(
      /confidence must be in \[0, 1\]/,
    );
  });
});

describe("applyConfidenceThreshold", () => {
  it("keeps a confident answer", () => {
    const result = applyConfidenceThreshold({ category: "Travel", confidence: 0.85 }, 0.6);

    expect(result.category).toBe("Travel");
    expect(result.used_fallback).toBe(false);
  });

  it("falls back below the threshold", () => {
    const result = applyConfidenceThreshold({ category: "Travel", confidence: 0.4 }, 0.6);

    expect(result.category).toBe("Other");
    expect(result.used_fallback).toBe(true);
    // The original confidence is preserved — the caller may want to show it.
    expect(result.confidence).toBeCloseTo(0.4);
  });

  it("treats the boundary as confident", () => {
    // Exactly at the threshold counts as confident. Worth pinning: an
    // off-by-one here silently changes behaviour for a whole band of inputs.
    const result = applyConfidenceThreshold({ category: "Housing", confidence: 0.6 }, 0.6);

    expect(result.category).toBe("Housing");
    expect(result.used_fallback).toBe(false);
  });
});

describe("categorise (mocked at the LLM boundary)", () => {
  it("handles the happy path", async () => {
    const client = FakeLlmClient.returning("Food & Dining", 0.95);

    const result = await categorise("Starbucks", 5.45, client, 0.6);

    expect(result.category).toBe("Food & Dining");
    expect(result.used_fallback).toBe(false);
    expect(client.callCount).toBe(1);
  });

  it("passes the prompts through", async () => {
    const client = FakeLlmClient.returning("Other", 0.9);

    await categorise("Starbucks", 5.45, client, 0.6);

    expect(client.lastUserPrompt).toContain("Starbucks");
    expect(client.lastSystemPrompt).toContain("Food & Dining");
  });

  it("surfaces contract violations", async () => {
    const client = new FakeLlmClient("{ nonsense");

    await expect(categorise("Starbucks", 5.45, client)).rejects.toThrow(ContractViolationError);
  });
});
