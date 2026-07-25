import type { Message as MessageType } from "../hooks/useStreamingChat";
import { ToolCallBlock } from "./ToolCallBlock";

export function Message({ message }: { message: MessageType }) {
  return (
    <div className={`message message--${message.role}`}>
      <div className="message__role">{message.role === "user" ? "You" : "Agent"}</div>
      <div className="message__body">
        {message.toolCalls.map((call) => (
          <ToolCallBlock key={call.id} call={call} />
        ))}
        {message.text && <div className="message__text">{message.text}</div>}
        {message.role === "assistant" && !message.finished && (
          <span className="message__cursor">▍</span>
        )}
      </div>
    </div>
  );
}
