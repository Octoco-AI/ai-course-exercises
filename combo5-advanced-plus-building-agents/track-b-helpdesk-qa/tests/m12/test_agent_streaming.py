"""Module 12, Step A.1 — the streaming agent loop.

Skips at module level until `run_agent_streaming` exists in `backend.agent`
— that's the expected state through Module 11.

Run just these with: pytest -m m12 tests/m12/test_agent_streaming.py
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from google.genai import types as gtypes

import backend.agent as agent_module

if not hasattr(agent_module, "run_agent_streaming"):
    pytest.skip(
        "run_agent_streaming not implemented yet — Module 12, Step A.1.",
        allow_module_level=True,
    )

run_agent_streaming = agent_module.run_agent_streaming

pytestmark = pytest.mark.m12


class _FakeGeminiStream:
    def __init__(self, parts: list):
        self._chunks = [
            SimpleNamespace(
                candidates=[SimpleNamespace(content=gtypes.Content(role="model", parts=parts))]
            )
        ]

    def __iter__(self):
        return iter(self._chunks)


class _FakeGeminiModels:
    def __init__(self, scripted_turns: list[list]):
        self._turns = list(scripted_turns)

    def generate_content_stream(self, **kwargs):  # noqa: ARG002
        if not self._turns:
            raise AssertionError("Agent made more calls than the script had responses for.")
        return _FakeGeminiStream(self._turns.pop(0))


class _FakeGeminiClient:
    def __init__(self, scripted):
        self.models = _FakeGeminiModels(scripted)


async def test_streaming_agent_terminates_on_text(settings_for_test, sandbox, monkeypatch):
    monkeypatch.setattr(
        "backend.agent.genai.Client",
        lambda api_key: _FakeGeminiClient([[gtypes.Part(text="Hello there")]]),
    )
    events = [
        event
        async for event in run_agent_streaming(
            "hi", settings=settings_for_test, tools=sandbox["tools"]
        )
    ]
    assert any("event: text" in e and "Hello there" in e for e in events)
    assert any("event: done" in e for e in events)


async def test_streaming_agent_dispatches_tool_then_finishes(settings_for_test, sandbox, monkeypatch):
    scripted = [
        [gtypes.Part(function_call=gtypes.FunctionCall(name="list_tickets", args={}))],
        [gtypes.Part(text="Here are the open tickets.")],
    ]
    monkeypatch.setattr("backend.agent.genai.Client", lambda api_key: _FakeGeminiClient(scripted))

    events = [
        event
        async for event in run_agent_streaming(
            "what's open?", settings=settings_for_test, tools=sandbox["tools"]
        )
    ]
    assert any("event: tool_call" in e and "list_tickets" in e for e in events)
    assert any("event: tool_result" in e for e in events)
    assert any("event: done" in e for e in events)
