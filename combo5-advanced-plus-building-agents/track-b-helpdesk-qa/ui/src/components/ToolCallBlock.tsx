import type { ToolCallEvent } from "../hooks/useStreamingChat";

/**
 * ToolCallBlock — Module 12, Step B.5. Renders one tool call as a
 * collapsible block: a header (status + name + args summary) and, when
 * expanded, the full arguments and result preview.
 *
 * This stub renders just enough to typecheck and not look broken — a flat
 * line with the tool name. Build the collapse/expand behaviour, the
 * running ("…") vs done ("✓") status, and the args/result detail view.
 */
export function ToolCallBlock({ call }: { call: ToolCallEvent }) {
  // TODO: Step B.5 — add `useState` for `expanded`; toggle it on click.
  // TODO: derive `status` from `call.resultPreview === undefined` ("running" vs "done").
  // TODO: render a one-line args summary (`k=v, k=v`), and, when expanded,
  //       the full args (JSON.stringify) and `call.resultPreview`.
  return (
    <div className="tool-call">
      <span className="tool-call__name">{call.name}</span>
    </div>
  );
}
