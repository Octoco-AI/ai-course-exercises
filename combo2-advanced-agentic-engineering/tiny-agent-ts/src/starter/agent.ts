import type { GoogleGenAI } from "@google/genai";

import { resolveModel } from "../shared/toolSchemas.js";
import type { OnEvent, Tools } from "../shared/types.js";

/**
 * The agent loop. YOU WRITE THIS (step 1).
 *
 * Thesis (Thorsten Ball, ampcode.com): *It's an LLM, a loop, and enough tokens.*
 *
 * The shape of the loop you're going to write:
 *
 *     const contents = [{ role: "user", parts: [{ text: userPrompt }] }]
 *     for (let turn = 1; turn <= maxTurns; turn += 1) {
 *         const response = await ai.models.generateContent({ model, contents, config })
 *         contents.push(candidate.content)          // don't forget this line
 *         const calls = parts with a .functionCall
 *         if (calls.length === 0) return joined text // done
 *         for (const call of calls) { dispatch it, collect a functionResponse part }
 *         contents.push({ role: "user", parts: responseParts })
 *     }
 *
 * Hints — everything you need is in `src/shared/`:
 *   - `import { dispatch } from "../shared/dispatch.js"` — routes a call to a tool,
 *     already written. Call it, don't rewrite it.
 *   - `SYSTEM_INSTRUCTION` and `TOOL_DECLARATIONS` from `../shared/toolSchemas.js`.
 *   - The config you need:
 *       { systemInstruction: SYSTEM_INSTRUCTION,
 *         tools: [{ functionDeclarations: TOOL_DECLARATIONS }],
 *         automaticFunctionCalling: { disable: true } }
 *     If you don't disable automatic function calling, you won't have an agent —
 *     you'll have a function Google called on your behalf.
 *   - The model's turn: `response.candidates?.[0]?.content`
 *   - Function calls live in `content.parts` where `part.functionCall` is set.
 *   - Send a result back: `{ functionResponse: { name, response: { result } } }`
 *   - Tool results go back with role **"user"**, not "tool" and not "function".
 *   - Termination: a turn with no function-call parts.
 *
 * Yes, it's `async`. Every network call in JavaScript is a Promise, so `await`
 * is unavoidable. It is plumbing, not the lesson.
 *
 * Start with the simplest version that handles the exploration prompts
 * (TODO.md items 1 and 2), then try the bug-fix prompt (item 3).
 */
export interface RunAgentOptions {
  model?: string;
  maxTurns?: number;
  onEvent?: OnEvent;
}

export async function runAgent(
  _userPrompt: string,
  _tools: Tools,
  _ai: GoogleGenAI,
  options: RunAgentOptions = {},
): Promise<string> {
  const _model = options.model ?? resolveModel();
  const _maxTurns = options.maxTurns ?? 20;

  // TODO: Step 1 — write the loop.
  throw new Error("Implement runAgent for step 1.");
}
