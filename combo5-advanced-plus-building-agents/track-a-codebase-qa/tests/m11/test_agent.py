"""Module 11 — agent-loop tests with a mocked Gemini client.

Runs the loop without hitting the real API. `test_agent_terminates_on_text`
only exercises Step 2 (the skeleton) and should pass early; the rest
exercise Step 4 (concurrent dispatch) and skip until it's implemented.

Skips at module level once `run_agent` no longer exists — Module 12, Step
A.1 renames it to `run_agent_streaming`; that's expected once you've caught
up past Module 11 (e.g. via `./scripts/checkpoint.sh m12-end`).

Run just these with: pytest -m m11 tests/m11/test_agent.py
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from google.genai import types as gtypes

import backend.agent as agent_module

if not hasattr(agent_module, "run_agent"):
    pytest.skip(
        "run_agent isn't defined — Module 12 already renamed it to run_agent_streaming.",
        allow_module_level=True,
    )

run_agent = agent_module.run_agent

pytestmark = pytest.mark.m11


class _FakeResponse:
    def __init__(self, parts: list):
        self.candidates = [SimpleNamespace(content=SimpleNamespace(parts=parts))]


class _FakeGeminiModels:
    def __init__(self, scripted_turns: list[list]):
        self._turns = list(scripted_turns)

    def generate_content(self, **kwargs):  # noqa: ARG002
        if not self._turns:
            raise AssertionError("Agent made more calls than the script had responses for.")
        return _FakeResponse(self._turns.pop(0))


class _FakeGeminiClient:
    def __init__(self, scripted):
        self.models = _FakeGeminiModels(scripted)


async def test_agent_terminates_on_text(settings_for_test, sandbox, monkeypatch):
    """Model replies with text only, no tool calls — Step 2 alone covers this."""
    monkeypatch.setattr(
        "backend.agent.genai.Client",
        lambda api_key: _FakeGeminiClient([[gtypes.Part(text="Hello there")]]),
    )
    result = await run_agent("hi", tools=sandbox["tools"], settings=settings_for_test)
    assert result == "Hello there"


async def test_agent_dispatches_tool_then_finishes(settings_for_test, sandbox, monkeypatch):
    """Model calls list_files, then replies with final text on turn 2. Needs Step 4."""
    scripted = [
        [gtypes.Part(function_call=gtypes.FunctionCall(name="list_files", args={"path": "."}))],
        [gtypes.Part(text="Here are the files.")],
    ]
    monkeypatch.setattr("backend.agent.genai.Client", lambda api_key: _FakeGeminiClient(scripted))

    try:
        result = await run_agent("what's here?", tools=sandbox["tools"], settings=settings_for_test)
    except NotImplementedError:
        pytest.skip("Tool dispatch not implemented yet — Module 11, Step 4.")

    assert result == "Here are the files."


async def test_agent_handles_tool_error_gracefully(settings_for_test, sandbox, monkeypatch):
    """A tool that errors comes back as an ERROR: string, not a crash. Needs Steps 3-4."""
    scripted = [
        [gtypes.Part(function_call=gtypes.FunctionCall(name="read_file", args={"path": "no-such.md"}))],
        [gtypes.Part(text="Sorry, that file doesn't exist.")],
    ]
    monkeypatch.setattr("backend.agent.genai.Client", lambda api_key: _FakeGeminiClient(scripted))

    try:
        result = await run_agent("read no-such.md", tools=sandbox["tools"], settings=settings_for_test)
    except NotImplementedError:
        pytest.skip("Tool dispatch not implemented yet — Module 11, Step 4.")

    assert result == "Sorry, that file doesn't exist."


async def test_agent_respects_max_turns_bound(settings_for_test, sandbox, monkeypatch):
    """The model keeps calling tools forever — the loop bails after max_agent_turns. Needs Step 4."""
    from dataclasses import replace

    bounded_settings = replace(settings_for_test, max_agent_turns=2)
    always_calls_a_tool = [
        gtypes.Part(function_call=gtypes.FunctionCall(name="list_files", args={"path": "."}))
    ]
    monkeypatch.setattr(
        "backend.agent.genai.Client",
        lambda api_key: _FakeGeminiClient([always_calls_a_tool, always_calls_a_tool]),
    )

    try:
        result = await run_agent("loop forever", tools=sandbox["tools"], settings=bounded_settings)
    except NotImplementedError:
        pytest.skip("Tool dispatch not implemented yet — Module 11, Step 4.")

    assert "did not finish within max turns" in result
