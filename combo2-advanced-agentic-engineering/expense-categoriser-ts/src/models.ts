import { z } from "zod";

/**
 * Keep this list short and stable — the prompt enumerates it. Don't reshuffle
 * without re-running the eval baseline; label order can subtly affect the LLM.
 */
export const CANONICAL_CATEGORIES = [
  "Food & Dining",
  "Transportation",
  "Shopping",
  "Entertainment",
  "Healthcare",
  "Utilities",
  "Housing",
  "Travel",
  "Personal Care",
  "Subscriptions",
  "Education",
  "Gifts & Donations",
  "Income",
  "Other",
] as const;

export type Category = (typeof CANONICAL_CATEGORIES)[number];

export const FALLBACK_CATEGORY: Category = "Other";

/** What the API caller sends. */
export const ExpenseIn = z.object({
  /** Transaction description as it appears on the statement. */
  description: z.string().min(1).max(500),
  /** Transaction amount in the user's currency. Negative = credit. */
  amount: z.number(),
});
export type ExpenseIn = z.infer<typeof ExpenseIn>;

/** What the API returns. */
export interface CategorisationOut {
  category: string;
  confidence: number;
  /**
   * True when the model's confidence fell below the threshold and we returned
   * "Other" as a fallback. Note this is a SUCCESSFUL response, not an error.
   */
  used_fallback: boolean;
}

/**
 * The schema we ask Gemini to produce. Kept separate from CategorisationOut so
 * we can wrap the raw model output with our fallback logic before returning it.
 *
 * Zod does double duty here: it validates the model's JSON *and* it is the
 * closest thing TypeScript has to Python's pydantic model.
 */
export const ModelResponse = z.object({
  category: z.string(),
  confidence: z.number().min(0).max(1),
});
export type ModelResponse = z.infer<typeof ModelResponse>;

/**
 * Thrown when the model's output violates the contract we asked for.
 *
 * This is the "the model started misbehaving" signal that the CE pipeline in
 * M12 watches for. It maps to HTTP 502, not 500 — the service is fine, the
 * model isn't.
 */
export class ContractViolationError extends Error {
  override readonly name = "ContractViolationError";
}
