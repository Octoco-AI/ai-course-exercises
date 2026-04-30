"""Shared pytest fixtures — Track B."""

from __future__ import annotations

from pathlib import Path

import chromadb
import pytest

from backend.settings import Settings
from backend.tools import ToolSet


@pytest.fixture
def sandbox(tmp_path: Path):
    """A temp workspace + a fresh Chroma collection seeded with a few KB articles."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "account-security.md").write_text(
        "# Account security\n\n## Two-factor authentication\n\nWe support TOTP via any authenticator app.\n",
        encoding="utf-8",
    )
    (workspace / "billing-and-plans.md").write_text(
        "# Plans\n\n## Refunds\n\nRefunds go through Apple or Google.\n",
        encoding="utf-8",
    )

    draft_replies = tmp_path / "draft-replies"
    escalations = tmp_path / "escalations"
    draft_replies.mkdir()
    escalations.mkdir()

    chroma_root = tmp_path / "chroma"
    client = chromadb.PersistentClient(path=str(chroma_root))
    collection = client.create_collection("test-kb")
    collection.add(
        documents=[
            "We support TOTP via any authenticator app. To enable, go to Settings.",
            "Refunds go through Apple or Google. Streakly can't issue them directly.",
            "Your streak grows by one each consecutive day you mark a habit done.",
        ],
        metadatas=[
            {"source": "account-security.md", "heading": "Two-factor authentication"},
            {"source": "billing-and-plans.md", "heading": "Refunds"},
            {"source": "streaks-and-tracking.md", "heading": "The basic rule"},
        ],
        ids=["a", "b", "c"],
    )

    tools = ToolSet(
        workspace_root=workspace,
        chroma_persist_root=chroma_root,
        chroma_collection_name="test-kb",
        draft_replies_root=draft_replies,
        escalations_root=escalations,
    )

    yield {
        "workspace": workspace,
        "draft_replies": draft_replies,
        "escalations": escalations,
        "tools": tools,
    }


@pytest.fixture
def settings_for_test(sandbox, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-do-not-use")
    return Settings(
        anthropic_api_key="test-key",
        model="claude-haiku-4-5",
        workspace_root=sandbox["workspace"],
        chroma_persist_root=sandbox["workspace"].parent / "chroma",
        chroma_collection_name="test-kb",
        draft_replies_root=sandbox["draft_replies"],
        escalations_root=sandbox["escalations"],
        max_agent_turns=5,
    )
