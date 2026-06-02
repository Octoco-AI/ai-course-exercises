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
          <h2>Try a Streakly support question</h2>
          <ul>
            <li>"How do I enable 2FA?"</li>
            <li>"My streak disappeared after I flew to Tokyo."</li>
            <li>"I was charged $49 and I don't have Plus."</li>
            <li>"My child signed up and I want the account deleted."</li>
          </ul>
          <p className="chat-panel__empty-hint-note">
            (The last two should escalate — watch the tool-call block for the red border.)
          </p>
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
