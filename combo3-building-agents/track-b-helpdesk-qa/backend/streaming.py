"""SSE event helpers — Track B. Identical shape to Track A's streaming.py so
the UI code carries over without modification.
"""

from __future__ import annotations

import json
from typing import Any


def sse_event(event_type: str, data: dict[str, Any]) -> str:
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
    if isinstance(value, list):
        preview = f"[{len(value)} items] " + ", ".join(map(str, value[:3]))
    elif isinstance(value, str):
        preview = value
    else:
        preview = str(value)
    if len(preview) > max_chars:
        preview = preview[: max_chars - 3] + "..."
    return preview.replace("\n", " ⏎ ")
