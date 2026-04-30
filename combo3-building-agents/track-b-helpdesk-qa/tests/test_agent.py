"""Agent tests with a mock Anthropic client — Track B.

Same structure as Track A's test_agent.py. Key Track-B-specific scenario:
confirming that a question requiring user-specific data results in an
escalate_to_human call.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.agent import run_agent_streaming


class _FakeTextStream:
    def __init__(self, chunks: list[str]):
        self._chunks = chunks

    def __iter__(self):
        return iter(self._chunks)


class _FakeStreamCtx:
    def __init__(self, chunks, content):
        self._chunks = chunks
        self._final = SimpleNamespace(content=content)

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
    def __init__(self, scripted):
        self._responses = list(scripted)

    def stream(self, **kwargs):  # noqa: ARG002
        if not self._responses:
            raise AssertionError("Agent made more calls than the script had.")
        chunks, content = self._responses.pop(0)
        return _FakeStreamCtx(chunks, content)


class _FakeAnthropic:
    def __init__(self, scripted):
        self.messages = _FakeMessages(scripted)


def _text(text: str):
    return SimpleNamespace(type="text", text=text)


def _tool_use(name: str, input_: dict, tool_id: str = "tid-1"):
    return SimpleNamespace(type="tool_use", id=tool_id, name=name, input=input_)


@pytest.mark.asyncio
async def test_agent_answers_kb_question_with_draft_reply(sandbox, settings_for_test, monkeypatch):
    """Model searches the KB, then drafts a reply, then finishes."""
    scripted = [
        ([], [_tool_use("search_kb", {"query": "enable 2FA"})]),
        ([], [_tool_use(
            "create_draft_reply",
            {
                "subject": "Re: How do I enable 2FA",
                "body": "Hi! Go to Settings → Account...",
                "tags": ["security"],
            },
            tool_id="tid-2",
        )]),
        (
            ["I've drafted a reply about enabling 2FA. A human will review and send."],
            [_text("I've drafted a reply about enabling 2FA. A human will review and send.")],
        ),
    ]
    monkeypatch.setattr(
        "backend.agent.anthropic.Anthropic",
        lambda api_key: _FakeAnthropic(scripted),
    )

    events = []
    async for event in run_agent_streaming(
        "How do I enable 2FA?",
        settings=settings_for_test,
        tools=sandbox["tools"],
    ):
        events.append(event)

    tool_calls = [e for e in events if "event: tool_call" in e]
    assert any("search_kb" in e for e in tool_calls)
    assert any("create_draft_reply" in e for e in tool_calls)
    assert any("event: done" in e for e in events)

    # A draft file actually appeared.
    drafts = list(sandbox["draft_replies"].glob("*.md"))
    assert len(drafts) == 1


@pytest.mark.asyncio
async def test_agent_escalates_for_account_specific_questions(sandbox, settings_for_test, monkeypatch):
    """Question about a specific user's data should escalate, not answer."""
    scripted = [
        ([], [_tool_use(
            "escalate_to_human",
            {
                "category": "billing",
                "summary": "User claims duplicate $49 charge; need to inspect Apple receipts.",
                "priority": "high",
            },
        )]),
        (
            ["I've escalated this to a human agent who can access your billing history."],
            [_text("I've escalated this to a human agent who can access your billing history.")],
        ),
    ]
    monkeypatch.setattr(
        "backend.agent.anthropic.Anthropic",
        lambda api_key: _FakeAnthropic(scripted),
    )

    events = []
    async for event in run_agent_streaming(
        "I was charged $49 but don't have Plus. Check what happened.",
        settings=settings_for_test,
        tools=sandbox["tools"],
    ):
        events.append(event)

    assert any("escalate_to_human" in e for e in events if "event: tool_call" in e)
    tickets = list(sandbox["escalations"].glob("*.md"))
    assert len(tickets) == 1
    assert "high" in tickets[0].name
    assert "billing" in tickets[0].name


@pytest.mark.asyncio
async def test_agent_handles_tool_errors_gracefully(sandbox, settings_for_test, monkeypatch):
    """A failed tool call (e.g. unknown escalation category) gets surfaced as
    ERROR text to the model, which can then correct and continue."""
    scripted = [
        # First attempt: bad category.
        ([], [_tool_use(
            "escalate_to_human",
            {"category": "garbage", "summary": "whatever"},
        )]),
        # Second attempt: corrected.
        ([], [_tool_use(
            "escalate_to_human",
            {"category": "other", "summary": "whatever", "priority": "low"},
            tool_id="tid-2",
        )]),
        (["Escalated."], [_text("Escalated.")]),
    ]
    monkeypatch.setattr(
        "backend.agent.anthropic.Anthropic",
        lambda api_key: _FakeAnthropic(scripted),
    )

    events = []
    async for event in run_agent_streaming(
        "whatever",
        settings=settings_for_test,
        tools=sandbox["tools"],
    ):
        events.append(event)

    # The first tool_result event contains ERROR text.
    tr_events = [e for e in events if "event: tool_result" in e]
    assert len(tr_events) == 2
    assert "ERROR" in tr_events[0]
    # And the agent recovered.
    assert any("event: done" in e for e in events)
