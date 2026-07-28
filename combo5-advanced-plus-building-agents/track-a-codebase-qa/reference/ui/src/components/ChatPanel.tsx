import { useEffect, useRef } from "react";
import type { Message as MessageType } from "../hooks/useStreamingChat";
import { Message } from "./Message";

export function ChatPanel({ messages }: { messages: MessageType[] }) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="chat-panel chat-panel--empty">
        <div className="chat-panel__empty-hint">
          <h2>Ask about TodoMagic</h2>
          <ul>
            <li>"How does authentication work?"</li>
            <li>"What's changed in the last few releases?"</li>
            <li>"How do I run the integration tests?"</li>
            <li>"Draft a patch that replaces the hard-coded session TTL with an env var."</li>
          </ul>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-panel">
      {messages.map((m, i) => (
        <Message key={i} message={m} />
      ))}
      <div ref={endRef} />
    </div>
  );
}
