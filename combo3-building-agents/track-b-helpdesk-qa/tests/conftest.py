"""Shared pytest fixtures for the Module 1 / Module 2 / Module 3 exercises — Track B."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def sandbox(tmp_path: Path):
    """A temp workspace with a couple of tickets + a ToolSet bound to it.

    Skips (rather than erroring) if `build_toolset` isn't implemented yet —
    that's the expected state of a fresh Module 1 starter.
    """
    from backend.tools import build_toolset

    workspace = tmp_path / "workspace"
    tickets = workspace / "tickets"
    tickets.mkdir(parents=True)
    (tickets / "TKT-1001.md").write_text(
        "Status: open\nCustomer: alice@example.com\nTheme: billing\n\n"
        "## Message\n\nI was charged twice this month.\n",
        encoding="utf-8",
    )
    (tickets / "TKT-1002.md").write_text(
        "Status: open\nCustomer: bob@example.com\nTheme: sync\n\n"
        "## Message\n\nMy streak reset overnight.\n",
        encoding="utf-8",
    )

    draft_replies = tmp_path / "draft-replies"
    draft_replies.mkdir()

    try:
        tools = build_toolset(workspace, draft_replies=draft_replies)
    except NotImplementedError:
        pytest.skip("build_toolset() not implemented yet — Module 1, Step 3d.")

    return {"workspace": workspace, "draft_replies": draft_replies, "tools": tools}


@pytest.fixture
def settings_for_test(sandbox):
    """A Settings instance pointed at the sandbox workspace (client mocked in tests)."""
    from backend.settings import Settings

    return Settings(
        anthropic_api_key="test-key",
        workspace_root=sandbox["workspace"],
        draft_replies_root=sandbox["draft_replies"],
        max_agent_turns=5,
    )
