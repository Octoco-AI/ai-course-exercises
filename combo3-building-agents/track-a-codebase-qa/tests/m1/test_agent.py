"""Module 1 — agent-loop tests with a mocked (sync) Anthropic client.

`test_agent_terminates_on_text` only exercises Step 2 (the skeleton) and
should pass early; the rest exercise Step 4 (tool dispatch) and skip until
it's implemented.

Skips at module level once `run_agent` no longer exists — Module 3, Part A
renames it to `run_agent_streaming`; that's expected once you've caught up
past Module 1/2 (e.g. via `./scripts/checkpoint.sh m3-end`).

Run just these with: pytest -m m1 tests/m1/test_agent.py
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import backend.agent as agent_module

if not hasattr(agent_module, "run_agent"):
    pytest.skip(
        "run_agent isn't defined — Module 3 already renamed it to run_agent_streaming.",
        allow_module_level=True,
    )

run_agent = agent_module.run_agent

pytestmark = pytest.mark.m1


def _text_block(text: str):
    return SimpleNamespace(type="text", text=text)


def _tool_use_block(name: str, input_: dict, tool_id: str = "tid-1"):
    return SimpleNamespace(type="tool_use", id=tool_id, name=name, input=input_)


class _FakeResponse:
    def __init__(self, content: list, stop_reason: str):
        self.content = content
        self.stop_reason = stop_reason


class _FakeMessages:
    def __init__(self, scripted: list[tuple[list, str]]):
        self._responses = list(scripted)

    def create(self, **kwargs):  # noqa: ARG002
        if not self._responses:
            raise AssertionError("Agent made more calls than the script had responses for.")
        content, stop_reason = self._responses.pop(0)
        return _FakeResponse(content, stop_reason)


class _FakeAnthropicClient:
    def __init__(self, scripted):
        self.messages = _FakeMessages(scripted)


def test_agent_terminates_on_text(settings_for_test, sandbox, monkeypatch):
    """Model replies with text only — Step 2 alone covers this."""
    monkeypatch.setattr(
        "backend.agent.anthropic.Anthropic",
        lambda api_key: _FakeAnthropicClient([([_text_block("Hello there")], "end_turn")]),
    )
    result = run_agent("hi", tools=sandbox["tools"], settings=settings_for_test)
    assert result == "Hello there"


def test_agent_dispatches_tool_then_finishes(settings_for_test, sandbox, monkeypatch):
    """Model calls list_files, then replies with final text on turn 2. Needs Step 4."""
    scripted = [
        ([_tool_use_block("list_files", {"path": "."})], "tool_use"),
        ([_text_block("Here are the files.")], "end_turn"),
    ]
    monkeypatch.setattr(
        "backend.agent.anthropic.Anthropic", lambda api_key: _FakeAnthropicClient(scripted)
    )

    try:
        result = run_agent("what's here?", tools=sandbox["tools"], settings=settings_for_test)
    except NotImplementedError:
        pytest.skip("Tool dispatch not implemented yet — Module 1, Step 4.")

    assert result == "Here are the files."


def test_agent_handles_tool_error_gracefully(settings_for_test, sandbox, monkeypatch):
    """A tool that errors comes back as an ERROR: string, not a crash. Needs Steps 3-4."""
    scripted = [
        ([_tool_use_block("read_file", {"path": "no-such.md"})], "tool_use"),
        ([_text_block("Sorry, that file doesn't exist.")], "end_turn"),
    ]
    monkeypatch.setattr(
        "backend.agent.anthropic.Anthropic", lambda api_key: _FakeAnthropicClient(scripted)
    )

    try:
        result = run_agent("read no-such.md", tools=sandbox["tools"], settings=settings_for_test)
    except NotImplementedError:
        pytest.skip("Tool dispatch not implemented yet — Module 1, Step 4.")

    assert result == "Sorry, that file doesn't exist."


def test_agent_respects_max_turns_bound(settings_for_test, sandbox, monkeypatch):
    """The model keeps calling tools forever — the loop bails after max_agent_turns. Needs Step 4."""
    from dataclasses import replace

    bounded_settings = replace(settings_for_test, max_agent_turns=2)
    always_calls_a_tool = ([_tool_use_block("list_files", {"path": "."})], "tool_use")
    monkeypatch.setattr(
        "backend.agent.anthropic.Anthropic",
        lambda api_key: _FakeAnthropicClient([always_calls_a_tool, always_calls_a_tool]),
    )

    try:
        result = run_agent("loop forever", tools=sandbox["tools"], settings=bounded_settings)
    except NotImplementedError:
        pytest.skip("Tool dispatch not implemented yet — Module 1, Step 4.")

    assert "did not finish within max turns" in result
