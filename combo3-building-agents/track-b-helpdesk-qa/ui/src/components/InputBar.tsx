import { useState, KeyboardEvent } from "react";

type Props = {
  onSend: (text: string) => void;
  onCancel: () => void;
  isStreaming: boolean;
};

export function InputBar({ onSend, onCancel, isStreaming }: Props) {
  const [text, setText] = useState("");

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function submit() {
    const trimmed = text.trim();
    if (!trimmed || isStreaming) return;
    onSend(trimmed);
    setText("");
  }

  return (
    <div className="input-bar">
      <textarea
        className="input-bar__textarea"
        placeholder="Paste a user's question here..."
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        rows={2}
        disabled={isStreaming}
      />
      {isStreaming ? (
        <button type="button" className="input-bar__button input-bar__button--cancel" onClick={onCancel}>
          Stop
        </button>
      ) : (
        <button type="button" className="input-bar__button" onClick={submit} disabled={!text.trim()}>
          Send
        </button>
      )}
    </div>
  );
}
