import type { LlmClient } from "../src/core.js";

/**
 * A canned LLM. The seam that makes the unit and API layers free and instant.
 *
 * Layer 1 (unit) and layer 2 (API contract) never call a real model — they test
 * OUR code. Layer 3 (evals) never uses this — it measures the model. Mixing the
 * two up is the single most common mistake when teams first add evals.
 */
export class FakeLlmClient implements LlmClient {
  lastSystemPrompt: string | undefined;
  lastUserPrompt: string | undefined;
  callCount = 0;

  constructor(private readonly response: string) {}

  async generate(systemPrompt: string, userPrompt: string): Promise<string> {
    this.lastSystemPrompt = systemPrompt;
    this.lastUserPrompt = userPrompt;
    this.callCount += 1;
    return this.response;
  }

  static returning(category: string, confidence: number): FakeLlmClient {
    return new FakeLlmClient(JSON.stringify({ category, confidence }));
  }
}

/** An LLM client that always throws — for testing the configuration-error path. */
export class ThrowingLlmClient implements LlmClient {
  constructor(private readonly error: Error) {}

  async generate(): Promise<string> {
    throw this.error;
  }
}
