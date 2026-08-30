import { GoogleGenAI } from "@google/genai";

import type { LlmClient } from "./core.js";

/**
 * Thin wrapper around `@google/genai`, implementing the {@link LlmClient} seam.
 *
 * Two settings matter for a classifier and are easy to miss:
 *
 *   - `responseMimeType: "application/json"` — ask for JSON rather than hoping
 *     for it. Halves the contract violations on its own.
 *   - `temperature: 0.1` — this is classification; we want near-determinism,
 *     not creativity.
 *
 * The client is constructed lazily so unit tests that never call `generate()`
 * don't need a key.
 */
export const DEFAULT_MODEL = "gemini-3.1-flash-lite";

export class GeminiClient implements LlmClient {
  private readonly apiKey: string | undefined;
  private readonly model: string;
  private client: GoogleGenAI | undefined;

  constructor(options: { apiKey?: string; model?: string } = {}) {
    this.apiKey = options.apiKey ?? process.env["GOOGLE_API_KEY"];
    this.model = options.model ?? process.env["GEMINI_MODEL"] ?? DEFAULT_MODEL;
  }

  private ensureClient(): GoogleGenAI {
    if (this.client === undefined) {
      if (!this.apiKey) {
        // A configuration problem, not a model problem — the API maps this to
        // 500, where a contract violation maps to 502.
        throw new Error(
          "GOOGLE_API_KEY is not set. Either add it to .env or pass apiKey explicitly.",
        );
      }
      this.client = new GoogleGenAI({ apiKey: this.apiKey });
    }
    return this.client;
  }

  async generate(systemPrompt: string, userPrompt: string): Promise<string> {
    const ai = this.ensureClient();

    const response = await ai.models.generateContent({
      model: this.model,
      contents: userPrompt,
      config: {
        systemInstruction: systemPrompt,
        responseMimeType: "application/json",
        temperature: 0.1,
      },
    });

    return response.text ?? "";
  }
}
