"""Module 3, Step A.2 — SSE event-shape tests.

`backend/streaming.py` doesn't exist on a fresh Module 1/2 starter —
that's expected; the whole module is skipped until it's created.

Run just these with: pytest -m m3 tests/m3/test_streaming.py
"""

from __future__ import annotations

import pytest

streaming = pytest.importorskip(
    "backend.streaming", reason="backend/streaming.py doesn't exist yet — Module 3, Step A.2."
)

pytestmark = pytest.mark.m3


def test_text_event_shape():
    event = streaming.text_event("hello")
    assert event.startswith("event: text\n")
    assert '"type": "text"' in event
    assert '"content": "hello"' in event
    assert event.endswith("\n\n")


def test_tool_call_event_shape():
    event = streaming.tool_call_event(name="list_files", args={"path": "."})
    assert event.startswith("event: tool_call\n")
    assert '"name": "list_files"' in event


def test_done_event_shape():
    event = streaming.done_event(turns=2, final_text="done")
    assert event.startswith("event: done\n")
    assert '"turns": 2' in event


def test_error_event_shape():
    event = streaming.error_event("boom")
    assert event.startswith("event: error\n")
    assert '"message": "boom"' in event


def test_truncate_preview_truncates_long_strings():
    preview = streaming.truncate_preview("x" * 500, max_chars=10)
    assert len(preview) <= 15  # a little slack for the ellipsis marker


def test_truncate_preview_summarises_lists():
    preview = streaming.truncate_preview(["a", "b", "c", "d"])
    assert preview.startswith("[4 items]")
