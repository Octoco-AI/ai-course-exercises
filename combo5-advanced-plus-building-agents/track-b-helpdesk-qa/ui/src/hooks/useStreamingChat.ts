/**
 * useStreamingChat — the hook that will consume the agent's SSE stream.
 *
 * Module 12, Steps B.2-B.3. Right now this is an inert stub: the types are
 * complete (so the rest of the scaffold — App.tsx, ChatPanel.tsx,
 * Message.tsx, InputBar.tsx — typechecks and renders), but `send` doesn't
 * talk to the backend yet. Typing and sending currently does nothing.
 *
 * Event types the real implementation will read (from backend/streaming.py,
 * once Module 12's Part A exists):
 *   text         → chunk of assistant text (accumulates)
 *   tool_call    → the agent called a tool (renders as a collapsed block)
 *   tool_result  → the tool returned (renders under its matching tool_call)
 *   done         → end of turn
 *   error        → something broke
 */

import { useCallback, useState } from "react";

export type ToolCallEvent = {
  id: string;
  name: string;
  args: Record<string, unknown>;
  resultPreview?: string;
};

export type Message = {
  role: "user" | "assistant";
  text: string;
  toolCalls: ToolCallEvent[];
  finished: boolean;
};

// -----------------------------------------------------------------------
// STEP B.2 — the SSE event union
// -----------------------------------------------------------------------
// TODO: define a discriminated union over the five event shapes the
//       backend emits (text / tool_call / tool_result / done / error).
//       See exercise.adoc Step B.2 for the exact shape.
// type SSEData = ...

export function useStreamingChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  // -----------------------------------------------------------------------
  // STEP B.3 — the hook
  // -----------------------------------------------------------------------
  // TODO: implement `send(userMessage)`:
  //   - Push a user message + a placeholder assistant message.
  //   - POST to /api/chat with an AbortController signal.
  //   - Read `response.body.getReader()`; decode chunks with a TextDecoder;
  //     split on "\n\n" to find complete SSE frames; parse the `data: ` line
  //     as JSON; dispatch on `.type` (see handleEvent's shape in
  //     exercise.adoc).
  //   - On AbortError, treat it as a clean stop (no error shown).
  // TODO: implement `cancel()` — abort the in-flight fetch.
  const send = useCallback(async (_userMessage: string) => {
    // TODO: Step B.3 — implement send(). Until then, typing and sending is
    // a no-op — this stub deliberately never throws, so the scaffold keeps
    // rendering while you build the rest of Part B.
    console.warn("useStreamingChat.send is not implemented yet — see Module 12, Step B.3.");
  }, []);

  const cancel = useCallback(() => {
    // TODO: Step B.3 — implement cancel() (Step B.7 wires it to a Stop button).
  }, []);

  return { messages, isStreaming, send, cancel };
}
