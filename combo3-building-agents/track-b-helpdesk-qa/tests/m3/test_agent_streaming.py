"""Module 3, Step A.1 — the streaming agent loop.

Skips at module level until `run_agent_streaming` exists in `backend.agent`
— that's the expected state through Module 1/2.

Run just these with: pytest -m m3 tests/m3/test_agent_streaming.py
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

import backend.agent as agent_module

if not hasattr(agent_module, "run_agent_streaming"):
    pytest.skip(
        "run_agent_streaming not implemented yet — Module 3, Step A.1.",
        allow_module_level=True,
    )

run_agent_streaming = agent_module.run_agent_streaming

pytestmark = pytest.mark.m3


class _FakeTextStream:
    def __init__(self, chunks: list[str]):
        self._chunks = chunks

    def __iter__(self):
        return iter(self._chunks)


class _FakeStreamCtx:
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

    def stream(self, **kwargs):  # noqa: ARG002
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


async def test_streaming_agent_terminates_on_text(settings_for_test, sandbox, monkeypatch):
    chunks = ["Hello ", "there"]
    content = [_text_block("Hello there")]
    monkeypatch.setattr(
        "backend.agent.anthropic.Anthropic",
        lambda api_key: _FakeAnthropicClient([(chunks, content)]),
    )

    events = [
        event
        async for event in run_agent_streaming(
            "hi", settings=settings_for_test, tools=sandbox["tools"]
        )
    ]
    assert any("event: text" in e and "Hello " in e for e in events)
    assert any("event: done" in e for e in events)


async def test_streaming_agent_dispatches_tool_then_finishes(settings_for_test, sandbox, monkeypatch):
    scripted = [
        ([], [_tool_use_block("list_tickets", {})]),
        (["Here are the open tickets."], [_text_block("Here are the open tickets.")]),
    ]
    monkeypatch.setattr(
        "backend.agent.anthropic.Anthropic", lambda api_key: _FakeAnthropicClient(scripted)
    )

    events = [
        event
        async for event in run_agent_streaming(
            "what's open?", settings=settings_for_test, tools=sandbox["tools"]
        )
    ]
    assert any("event: tool_call" in e and "list_tickets" in e for e in events)
    assert any("event: tool_result" in e for e in events)
    assert any("event: done" in e for e in events)
