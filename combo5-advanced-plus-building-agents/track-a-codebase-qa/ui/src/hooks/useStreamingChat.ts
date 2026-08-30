/**
 * useStreamingChat — the hook that consumes the agent's SSE stream.
 *
 * Module 12, Steps B.2-B.3 end state. Raw fetch + ReadableStream, no
 * framework — no EventSource, because we POST.
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

    const handleEvent = useCallback((data: SSEData) => {
        setMessages(prev => {
            const next = [...prev];
            const last = next[next.length - 1];

            switch (data.type) {
                case "text":
                    next[next.length - 1] = {
                        ...last,
                        text: last.text + data.content,
                    };
                    break;
                case "tool_call":
                    next[next.length - 1] = {
                        ...last,
                        toolCalls: [
                            ...last.toolCalls,
                            {
                                id: `${data.name}-${last.toolCalls.length}`,
                                name: data.name,
                                args: data.args,
                            },
                        ],
                    };
                    break;
                case "tool_result": {
                    // Match to the last tool_call with this name and no result yet.
                    const updatedToolCalls = [...last.toolCalls];
                    for (let i = updatedToolCalls.length - 1; i >= 0; i--) {
                        if (
                            updatedToolCalls[i].name === data.name &&
                            !updatedToolCalls[i].resultPreview
                        ) {
                            updatedToolCalls[i] = {
                                ...updatedToolCalls[i],
                                resultPreview: data.preview,
                            };
                            break;
                        }
                    }
                    next[next.length - 1] = {
                        ...last,
                        toolCalls: updatedToolCalls,
                    };
                    break;
                }
                case "done":
                    next[next.length - 1] = { ...last, finished: true };
                    break;
                case "error":
                    next[next.length - 1] = {
                        ...last,
                        text: last.text + `\n\n[ERROR: ${data.message}]`,
                        finished: true,
                    };
                    break;
            }

            return next;
        });
    }, []);

    const send = useCallback(async (userMessage: string) => {
        // Push user turn + placeholder assistant turn.
        setMessages(prev => [
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

            if (!response.body) {
                throw new Error("No response body");
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value, { stream: true });
                console.log("[SSE chunk]", chunk);
                buffer += chunk;

                // Parse complete SSE events (terminated by \n\n).
                const events = buffer.split("\n\n");
                buffer = events.pop() ?? "";

                for (const eventBlock of events) {
                    const dataLine = eventBlock
                        .split("\n")
                        .find(l => l.startsWith("data: "));
                    if (!dataLine) continue;

                    let data: SSEData;
                    try {
                        data = JSON.parse(dataLine.slice(6));
                    } catch {
                        console.log("[SSE event] <unparseable>", dataLine);
                        continue;
                    }

                    console.log("[SSE event]", data);
                    handleEvent(data);
                }
            }
        } catch (err) {
            if ((err as Error).name === "AbortError") {
                // User cancelled. Clean.
            } else {
                handleEvent({
                    type: "error",
                    message: (err as Error).message,
                });
            }
        } finally {
            setIsStreaming(false);
            abortController.current = null;
        }
    }, [handleEvent]);

    const cancel = useCallback(() => {
        abortController.current?.abort();
    }, []);

    return { messages, isStreaming, send, cancel };
}
