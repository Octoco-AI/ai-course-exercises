import {
  CANONICAL_CATEGORIES,
  ContractViolationError,
  FALLBACK_CATEGORY,
  ModelResponse,
  type CategorisationOut,
} from "./models.js";

/**
 * The categorisation logic.
 *
 * Deliberately pulls apart the pieces that matter for three-layer testing:
 *
 *   - `buildPrompt`               → pure function, unit-test with exact assertions.
 *   - `parseResponse`             → pure function, unit-test.
 *   - `applyConfidenceThreshold`  → pure function, unit-test.
 *   - `categorise` (the top level) → calls Gemini; integration-test with a real
 *                                    key, mock at the LLM boundary for unit tests.
 *
 * Herman's blog "Testing the Untestable" says: test the deterministic parts
 * traditionally, test the AI boundary for contract conformance, and measure the
 * AI itself via evals at scale. This module is the code under test for all three.
 */

export const DEFAULT_CONFIDENCE_THRESHOLD = 0.6;

const SYSTEM_PROMPT_TEMPLATE = `You are an expense-categorisation assistant for a personal finance app.

Given a transaction description and amount, pick the single best category from this list:

{categories}

Respond with a JSON object of exactly this shape:

  {"category": "<one of the categories above>", "confidence": <0.0-1.0>}

Rules:
- Use only categories from the list above. No new categories.
- "confidence" is your self-reported certainty. Use 0.9+ for obvious matches
  (grocery store -> Food & Dining), 0.5-0.7 for ambiguous cases, below 0.5
  for genuinely unclear items.
- Do not explain. Do not add extra keys. Respond with JSON only.
`;

/** Build the user-turn prompt. Unit-tested for construction correctness. */
export function buildPrompt(description: string, amount: number): string {
  return `Transaction: "${description}"\nAmount: ${amount.toFixed(2)}`;
}

/** Render the system prompt with the canonical category list. */
export function buildSystemPrompt(
  categories: readonly string[] = CANONICAL_CATEGORIES,
): string {
  const joined = categories.map((c) => `  - ${c}`).join("\n");
  return SYSTEM_PROMPT_TEMPLATE.replace("{categories}", joined);
}

/**
 * Parse and validate the model's JSON output.
 *
 * Throws {@link ContractViolationError} on malformed JSON, unknown category, or
 * out-of-range confidence. The caller decides how to handle that (HTTP 502?
 * Fall back to "Other"? Product policy).
 */
export function parseResponse(
  raw: string,
  validCategories: readonly string[] = CANONICAL_CATEGORIES,
): ModelResponse {
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch (err) {
    throw new ContractViolationError(
      `model response is not valid JSON: ${(err as Error).message}`,
    );
  }

  if (typeof data !== "object" || data === null || Array.isArray(data)) {
    throw new ContractViolationError(
      `model response must be a JSON object, got ${Array.isArray(data) ? "array" : typeof data}`,
    );
  }

  const parsed = ModelResponse.safeParse(data);
  if (!parsed.success) {
    const issue = parsed.error.issues[0];
    // Zod distinguishes "wasn't there" from "was the wrong shape"; the model
    // does both, and the message needs to say which.
    const detail = issue ? `${issue.path.join(".") || "root"}: ${issue.message}` : "unknown";

    if (issue?.path[0] === "confidence" && issue.code === "too_small") {
      throw new ContractViolationError(`confidence must be in [0, 1], got ${(data as Record<string, unknown>)["confidence"]}`);
    }
    if (issue?.path[0] === "confidence" && issue.code === "too_big") {
      throw new ContractViolationError(`confidence must be in [0, 1], got ${(data as Record<string, unknown>)["confidence"]}`);
    }

    throw new ContractViolationError(`model response is missing required fields: ${detail}`);
  }

  if (!validCategories.includes(parsed.data.category)) {
    throw new ContractViolationError(
      `model returned unknown category '${parsed.data.category}'; ` +
        `expected one of [${validCategories.join(", ")}]`,
    );
  }

  return parsed.data;
}

/**
 * Graceful degradation: if confidence is below the threshold, return the
 * fallback category instead of the model's (uncertain) answer.
 *
 * From Herman's blog: `if confidence < threshold: show 'popular in similar
 * situations'`. For expense categorisation the analogue is "Other", which the
 * user can manually re-classify.
 */
export function applyConfidenceThreshold(
  response: ModelResponse,
  threshold: number,
  fallbackCategory: string = FALLBACK_CATEGORY,
): CategorisationOut {
  if (response.confidence < threshold) {
    return {
      category: fallbackCategory,
      confidence: response.confidence,
      used_fallback: true,
    };
  }
  return {
    category: response.category,
    confidence: response.confidence,
    used_fallback: false,
  };
}

/**
 * Narrow interface so tests can substitute a fake without touching Gemini.
 *
 * This seam is the whole reason the unit tests need no API key and cost nothing.
 * M11 leans on it heavily — notice that the eval suite deliberately does NOT use
 * it, because evals measure the real model.
 */
export interface LlmClient {
  /** Return the raw JSON string the model produced. */
  generate(systemPrompt: string, userPrompt: string): Promise<string>;
}

/** Categorise a single expense. The function three-layer-tested above. */
export async function categorise(
  description: string,
  amount: number,
  client: LlmClient,
  confidenceThreshold?: number,
): Promise<CategorisationOut> {
  const threshold = confidenceThreshold ?? resolveThreshold();

  const systemPrompt = buildSystemPrompt();
  const userPrompt = buildPrompt(description, amount);

  const raw = await client.generate(systemPrompt, userPrompt);
  const parsed = parseResponse(raw);
  return applyConfidenceThreshold(parsed, threshold);
}

function resolveThreshold(): number {
  const raw = process.env["CONFIDENCE_THRESHOLD"];
  const parsed = raw === undefined ? Number.NaN : Number.parseFloat(raw);
  return Number.isFinite(parsed) ? parsed : DEFAULT_CONFIDENCE_THRESHOLD;
}
