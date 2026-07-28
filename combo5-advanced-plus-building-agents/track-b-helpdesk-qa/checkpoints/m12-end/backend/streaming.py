"""SSE event shapes the backend streams to the UI. Module 12, Step A.2."""

from __future__ import annotations

import json
from typing import Any


def sse_event(event_type: str, data: dict[str, Any]) -> str:
    """Format a single SSE event as a string ready to write to the response."""
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
        preview = preview[:max_chars] + "…"
    return preview.replace("\n", " ⏎ ")
