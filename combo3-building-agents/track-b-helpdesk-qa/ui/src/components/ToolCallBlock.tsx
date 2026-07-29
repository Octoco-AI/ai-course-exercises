import { useState } from "react";
import type { ToolCallEvent } from "../hooks/useStreamingChat";

/**
 * ToolCallBlock — Module 12, Step B.5 end state. Collapsible; shows a
 * running/done status, a one-line args summary, and (expanded) the full
 * args + result preview.
 */
export function ToolCallBlock({ call }: { call: ToolCallEvent }) {
  const [expanded, setExpanded] = useState(false);
  const status = call.resultPreview === undefined ? "running" : "done";

  const argsPreview = Object.entries(call.args)
    .map(([k, v]) => `${k}=${formatArgValue(v)}`)
    .join(", ");

  return (
    <div className={`tool-call tool-call--${status}`}>
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
