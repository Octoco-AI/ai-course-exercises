"""Shared pytest fixtures for the Module 11 / Module 12 exercises."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def sandbox(tmp_path: Path):
    """A temporary workspace with a couple of files + a ToolSet bound to it.

    Skips (rather than erroring) if `build_toolset` isn't implemented yet —
    that's the expected state of a fresh Module 11 starter.
    """
    from backend.tools import build_toolset

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sandbox\n\nThis is a test workspace.\n", encoding="utf-8")
    (workspace / "src").mkdir()
    (workspace / "src" / "hello.py").write_text("def hello(): return 'hi'\n", encoding="utf-8")

    try:
        tools = build_toolset(workspace)
    except NotImplementedError:
        pytest.skip("build_toolset() not implemented yet — Module 11, Step 3d.")

    return {"workspace": workspace, "tools": tools}


@pytest.fixture
def settings_for_test(sandbox):
    """A Settings instance pointed at the sandbox workspace (Gemini path, mocked in tests)."""
    from backend.settings import Settings

    return Settings(
        provider="gemini",
        google_api_key="test-key",
        anthropic_api_key="",
        workspace_root=sandbox["workspace"],
        max_agent_turns=5,
    )
