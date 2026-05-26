import { useState } from "react";
import type { ToolCallEvent } from "../hooks/useStreamingChat";

export function ToolCallBlock({ call }: { call: ToolCallEvent }) {
  const [expanded, setExpanded] = useState(false);
  const status = call.resultPreview === undefined ? "running" : "done";

  const argsPreview = Object.entries(call.args)
    .map(([k, v]) => `${k}=${formatArgValue(v)}`)
    .join(", ");

  // Helpdesk-specific visual flavour: the escalate_to_human tool gets a
  // red tint since it's a "flag for human" action, not a neutral read.
  const extra = call.name === "escalate_to_human" ? " tool-call--escalation" : "";

  return (
    <div className={`tool-call tool-call--${status}${extra}`}>
      <button
        className="tool-call__header"
        onClick={() => setExpanded((e) => !e)}
        type="button"
      >
        <span className="tool-call__chevron">{expanded ? "▾" : "▸"}</span>
        <span className="tool-call__name">{call.name}</span>
        <span className="tool-call__args">({argsPreview})</span>
        <span className="tool-call__status">{status === "running" ? "…" : "✓"}</span>
      </button>
      {expanded && call.resultPreview !== undefined && (
        <pre className="tool-call__result">{call.resultPreview}</pre>
      )}
    </div>
  );
}

function formatArgValue(v: unknown): string {
  if (typeof v === "string") {
    return v.length > 60 ? `"${v.slice(0, 57)}..."` : `"${v}"`;
  }
  return JSON.stringify(v);
}
