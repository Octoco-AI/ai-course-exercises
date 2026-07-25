"""SSE event shapes the backend streams to the UI.

Four event types:
  - `text`      → a chunk of the model's text reply
  - `tool_call` → the model decided to call a tool (user sees "Calling X...")
  - `tool_result`  → the tool's output (usually collapsed in the UI)
  - `done`      → end of turn, with some summary metadata
  - `error`     → structured failure

Events are JSON objects, serialised one per SSE message (`data: {json}\n\n`).
Helpers in this module produce the right SSE-framed strings.
"""

from __future__ import annotations

import json
from typing import Any


def sse_event(event_type: str, data: dict[str, Any]) -> str:
    """Format a single SSE event as a string ready to write to the response."""
    # Include the event name so the EventSource on the client can use
    # .addEventListener('tool_call', ...). Works even if the client uses a
    # simple onmessage handler since we also include the type in `data`.
    payload = {"type": event_type, **data}
    return f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"


def text_event(chunk: str) -> str:
    return sse_event("text", {"content": chunk})


def tool_call_event(name: str, args: dict[str, Any]) -> str:
    return sse_event("tool_call", {"name": name, "args": args})


def tool_result_event(name: str, result_preview: str) -> str:
    return sse_event("tool_result", {"name": name, "preview": result_preview})


def done_event(turns: int, final_text: str) -> str:
    return sse_event("done", {"turns": turns, "final_text": final_text})


def error_event(message: str) -> str:
    return sse_event("error", {"message": message})


def truncate_preview(value: Any, max_chars: int = 300) -> str:
    """Make a short human-readable preview of a tool result for the UI.

    The full tool result goes back to the LLM; this is only for display.
    """
    if isinstance(value, list):
        preview = f"[{len(value)} items] " + ", ".join(map(str, value[:3]))
    elif isinstance(value, str):
        preview = value
    else:
        preview = str(value)
    if len(preview) > max_chars:
        preview = preview[: max_chars - 3] + "..."
    # SSE can't handle raw newlines in the data; collapse for the preview.
    return preview.replace("\n", " ⏎ ")
