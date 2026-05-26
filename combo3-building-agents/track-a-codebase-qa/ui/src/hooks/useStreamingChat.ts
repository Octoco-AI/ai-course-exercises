/**
 * useStreamingChat — the hook that consumes the agent's SSE stream.
 *
 * This is the pedagogical centrepiece of the UI side of Combo 3 M3b. It
 * reads SSE events from `/api/chat` and maintains a list of messages
 * reactively. Raw fetch + ReadableStream, no framework. ~80 lines.
 *
 * Event types it expects (from backend/streaming.py):
 *   text         → chunk of assistant text (accumulates)
 *   tool_call    → the agent called a tool (renders as a collapsed block)
 *   tool_result  → the tool returned (renders under its matching tool_call)
 *   done         → end of turn
 *   error        → something broke
 */

import { useCallback, useRef, useState } from "react";

export type ToolCallEvent = {
  id: string;        // client-generated, so we can match tool_result to tool_call
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

type SSEData =
  | { type: "text"; content: string }
  | { type: "tool_call"; name: string; args: Record<string, unknown> }
  | { type: "tool_result"; name: string; preview: string }
  | { type: "done"; turns: number; final_text: string }
  | { type: "error"; message: string };

export function useStreamingChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortController = useRef<AbortController | null>(null);

  const send = useCallback(async (userMessage: string) => {
    // Push the user turn and a placeholder assistant turn that we'll fill in.
    setMessages((prev) => [
      ...prev,
      { role: "user", text: userMessage, toolCalls: [], finished: true },
      { role: "assistant", text: "", toolCalls: [], finished: false },
    ]);
    setIsStreaming(true);

    abortController.current = new AbortController();
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage }),
        signal: abortController.current.signal,
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // SSE messages are separated by a blank line.
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          const dataLine = part.split("\n").find((l) => l.startsWith("data: "));
          if (!dataLine) continue;
          try {
            const payload: SSEData = JSON.parse(dataLine.slice(6));
            handleEvent(payload);
          } catch {
            // ignore malformed chunks — usually a heartbeat or a split message
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        appendError(`${(err as Error).message}`);
      }
    } finally {
      setIsStreaming(false);
      abortController.current = null;
      // Mark the latest assistant message finished no matter how the loop ended.
      setMessages((prev) =>
        prev.map((m, i) =>
          i === prev.length - 1 && m.role === "assistant" ? { ...m, finished: true } : m,
        ),
      );
    }
  }, []);

  const cancel = useCallback(() => {
    abortController.current?.abort();
  }, []);

  function handleEvent(ev: SSEData) {
    setMessages((prev) => {
      const next = [...prev];
      const last = { ...next[next.length - 1] };
      if (last.role !== "assistant") return prev;

      switch (ev.type) {
        case "text":
          last.text += ev.content;
          break;
        case "tool_call":
          last.toolCalls = [
            ...last.toolCalls,
            { id: crypto.randomUUID(), name: ev.name, args: ev.args },
          ];
          break;
        case "tool_result": {
          // Match to the most recent matching tool_call by name.
          const updated = [...last.toolCalls];
          for (let i = updated.length - 1; i >= 0; i--) {
            if (updated[i].name === ev.name && updated[i].resultPreview === undefined) {
              updated[i] = { ...updated[i], resultPreview: ev.preview };
              break;
            }
          }
          last.toolCalls = updated;
          break;
        }
        case "done":
          last.finished = true;
          break;
        case "error":
          last.text += `\n\n**ERROR:** ${ev.message}`;
          last.finished = true;
          break;
      }
      next[next.length - 1] = last;
      return next;
    });
  }

  function appendError(msg: string) {
    setMessages((prev) => [
      ...prev,
      { role: "assistant", text: `**ERROR:** ${msg}`, toolCalls: [], finished: true },
    ]);
  }

  return { messages, isStreaming, send, cancel };
}
