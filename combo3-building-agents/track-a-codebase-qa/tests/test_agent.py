"""Agent-level tests with a mock Anthropic client.

Runs the full loop without hitting the real API. Confirms the loop
dispatches tools correctly and terminates when the model stops calling them.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from backend.agent import run_agent_streaming


class _FakeTextStream:
    """Mimic anthropic SDK's `.text_stream` iterator."""

    def __init__(self, chunks: list[str]):
        self._chunks = chunks

    def __iter__(self):
        return iter(self._chunks)


class _FakeStreamCtx:
    """Mimic the `.stream(...)` context manager."""

    def __init__(self, chunks: list[str], content_blocks: list[Any]):
        self._chunks = chunks
        self._final = SimpleNamespace(content=content_blocks)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def text_stream(self):
        return _FakeTextStream(self._chunks)

    def get_final_message(self):
        return self._final


class _FakeMessages:
    def __init__(self, scripted_responses: list[tuple[list[str], list[Any]]]):
        self._responses = list(scripted_responses)

    def stream(self, **kwargs):  # noqa: ARG002 — mirror the real API's signature
        if not self._responses:
            raise AssertionError("Agent made more calls than the script had responses for.")
        chunks, content = self._responses.pop(0)
        return _FakeStreamCtx(chunks, content)


class _FakeAnthropicClient:
    def __init__(self, scripted):
        self.messages = _FakeMessages(scripted)


def _text_block(text: str):
    return SimpleNamespace(type="text", text=text)


def _tool_use_block(name: str, input_: dict, tool_id: str = "tid-1"):
    return SimpleNamespace(type="tool_use", id=tool_id, name=name, input=input_)


@pytest.mark.asyncio
async def test_agent_terminates_on_no_tool_use(sandbox, settings_for_test, monkeypatch):
    """Model replies with text only — agent yields the text and a `done`."""
    chunks = ["Hello ", "there"]
    content = [_text_block("Hello there")]
    monkeypatch.setattr(
        "backend.agent.anthropic.Anthropic",
        lambda api_key: _FakeAnthropicClient([(chunks, content)]),
    )

    events = []
    async for event in run_agent_streaming(
        "hi",
        settings=settings_for_test,
        tools=sandbox["tools"],
    ):
        events.append(event)

    # text events for both chunks + a done event.
    assert any("event: text" in e and "Hello " in e for e in events)
    assert any("event: text" in e and "there" in e for e in events)
    assert any("event: done" in e for e in events)


@pytest.mark.asyncio
async def test_agent_dispatches_tool_then_finishes(sandbox, settings_for_test, monkeypatch):
    """Model calls list_files, then replies with final text in a second turn."""
    scripted = [
        # Turn 1: tool_use only, no text.
        ([], [_tool_use_block("list_files", {"path": "."})]),
        # Turn 2: text only — terminates.
        (["Here are the files."], [_text_block("Here are the files.")]),
    ]
    monkeypatch.setattr(
        "backend.agent.anthropic.Anthropic",
        lambda api_key: _FakeAnthropicClient(scripted),
    )

    events = []
    async for event in run_agent_streaming(
        "what's here?",
        settings=settings_for_test,
        tools=sandbox["tools"],
    ):
        events.append(event)

    assert any("event: tool_call" in e and "list_files" in e for e in events)
    assert any("event: tool_result" in e for e in events)
    assert any("event: done" in e for e in events)
    # Two turns used.
    # (We don't check an exact turn count; the done event carries it in the JSON payload.)


@pytest.mark.asyncio
async def test_agent_handles_tool_error_gracefully(sandbox, settings_for_test, monkeypatch):
    """A tool that returns ERROR: string is passed back to the model, which
    can then finish. Loop does NOT raise."""
    scripted = [
        # Turn 1: request a read of a missing file.
        ([], [_tool_use_block("read_file", {"path": "no-such.md"})]),
        # Turn 2: the model explains the error and finishes.
        (["Sorry, that file doesn't exist."], [_text_block("Sorry, that file doesn't exist.")]),
    ]
    monkeypatch.setattr(
        "backend.agent.anthropic.Anthropic",
        lambda api_key: _FakeAnthropicClient(scripted),
    )

    events = []
    async for event in run_agent_streaming(
        "read no-such.md",
        settings=settings_for_test,
        tools=sandbox["tools"],
    ):
        events.append(event)

    # The tool_result event should mention the ERROR string, not crash.
    tr_events = [e for e in events if "event: tool_result" in e]
    assert len(tr_events) == 1
    assert "ERROR" in tr_events[0]
    # And we terminated normally.
    assert any("event: done" in e for e in events)
