import type { Content, GoogleGenAI, Part } from "@google/genai";

import { dispatch } from "../shared/dispatch.js";
import { SYSTEM_INSTRUCTION, TOOL_DECLARATIONS, resolveModel } from "../shared/toolSchemas.js";
import type { OnEvent, Tools } from "../shared/types.js";

/**
 * The agent loop — complete worked solution.
 *
 * Thesis (Thorsten Ball, ampcode.com): *It's an LLM, a loop, and enough tokens.*
 *
 * What the loop does, in one glance:
 *
 *     contents = [userPrompt]
 *     while turn < maxTurns:
 *         response = await ai.models.generateContent(contents, tools)
 *         contents.push(response.candidates[0].content)   // the most-forgotten line
 *         calls = function calls in the response
 *         if no calls: return the text                    // done
 *         for each call: contents.push(functionResponse)
 *
 * Note it is `async`. The Python original is deliberately synchronous — its
 * facilitator notes say "not a chance to teach asyncio". In JavaScript every
 * network call is a Promise, so `await` is unavoidable here. It is plumbing, not
 * the lesson: read past it and look at the loop.
 */
export interface RunAgentOptions {
  model?: string;
  maxTurns?: number;
  onEvent?: OnEvent;
}

export async function runAgent(
  userPrompt: string,
  tools: Tools,
  ai: GoogleGenAI,
  options: RunAgentOptions = {},
): Promise<string> {
  const model = options.model ?? resolveModel();
  const maxTurns = options.maxTurns ?? 20;
  const onEvent = options.onEvent;

  // Conversation state. Gemini's "contents" is an ordered list of turns
  // alternating between role "user" and role "model". Tool results go back as a
  // *user* turn whose parts are functionResponse parts.
  const contents: Content[] = [{ role: "user", parts: [{ text: userPrompt }] }];

  for (let turn = 1; turn <= maxTurns; turn += 1) {
    onEvent?.({ type: "turn_start", turn });

    const response = await ai.models.generateContent({
      model,
      contents,
      config: {
        systemInstruction: SYSTEM_INSTRUCTION,
        tools: [{ functionDeclarations: TOOL_DECLARATIONS }],
        // We want to SEE the loop. The SDK would otherwise run the tools itself
        // and return only the final text — great for production, bad for
        // learning. This is the single most important line in the config.
        automaticFunctionCalling: { disable: true },
      },
    });

    const candidate = response.candidates?.[0];
    if (!candidate?.content) {
      return `ERROR: model returned no content (finishReason: ${candidate?.finishReason ?? "none"})`;
    }

    // Append the model's turn BEFORE doing anything else. Forget this and the
    // model re-reads a context that never contains its own tool calls, so it
    // asks for the same thing forever. It is the #1 failure here.
    contents.push(candidate.content);

    const parts = candidate.content.parts ?? [];
    const calls = parts.flatMap((part) => (part.functionCall ? [part.functionCall] : []));

    if (calls.length === 0) {
      // No tool calls -> the model signalled it is done.
      const finalText = parts.map((part) => part.text ?? "").join("");
      onEvent?.({ type: "final", text: finalText, turns: turn });
      return finalText;
    }

    // Execute every call and collect the responses.
    const responseParts: Part[] = [];
    for (const call of calls) {
      const name = call.name ?? "";
      const args = (call.args ?? {}) as Record<string, unknown>;
      onEvent?.({ type: "tool_call", name, args });

      const result = dispatch(tools, name, args);

      onEvent?.({ type: "tool_result", name, result });
      responseParts.push({ functionResponse: { name, response: { result } } });
    }

    // Send all tool responses back in a single user turn.
    contents.push({ role: "user", parts: responseParts });
  }

  return `ERROR: agent did not finish within ${maxTurns} turns`;
}
