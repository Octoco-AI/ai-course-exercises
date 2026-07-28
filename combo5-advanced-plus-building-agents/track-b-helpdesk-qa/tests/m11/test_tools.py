"""Module 11, Phase 1 — tool-level tests.

Run just these with: pytest -m m11 tests/m11/test_tools.py
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.m11


def test_list_tickets_lists_all(sandbox):
    result = sandbox["tools"].dispatch("list_tickets", {})
    assert "TKT-1001" in result
    assert "TKT-1002" in result
    assert "billing" in result


def test_read_ticket_reads_contents(sandbox):
    result = sandbox["tools"].dispatch("read_ticket", {"ticket_id": "TKT-1001"})
    assert "charged twice" in result


def test_read_ticket_missing_returns_error_string(sandbox):
    result = sandbox["tools"].dispatch("read_ticket", {"ticket_id": "TKT-99999"})
    assert result.startswith("ERROR:")


def test_read_ticket_escape_attempt_returns_error_string(sandbox):
    result = sandbox["tools"].dispatch("read_ticket", {"ticket_id": "../../../etc/passwd"})
    assert result.startswith("ERROR:")


def test_draft_reply_writes_file_without_mutating_ticket(sandbox):
    tools = sandbox["tools"]
    original = (sandbox["workspace"] / "tickets" / "TKT-1001.md").read_text()

    result = tools.dispatch(
        "draft_reply", {"ticket_id": "TKT-1001", "body": "We've refunded the duplicate charge."}
    )
    assert "OK" in result or "written" in result.lower()

    # Ticket itself is untouched.
    assert (sandbox["workspace"] / "tickets" / "TKT-1001.md").read_text() == original

    # A draft file exists.
    drafts = list(sandbox["draft_replies"].glob("*.md"))
    assert len(drafts) == 1
    assert "refunded" in drafts[0].read_text()


def test_draft_reply_rejects_empty_body(sandbox):
    result = sandbox["tools"].dispatch("draft_reply", {"ticket_id": "TKT-1001", "body": "   "})
    assert result.startswith("ERROR:")


def test_dispatch_unknown_tool_returns_error_string(sandbox):
    result = sandbox["tools"].dispatch("delete_everything", {})
    assert result.startswith("ERROR:")


def test_dispatch_bad_arguments_returns_error_string(sandbox):
    result = sandbox["tools"].dispatch("read_ticket", {"nonexistent_kwarg": "x"})
    assert result.startswith("ERROR:")
