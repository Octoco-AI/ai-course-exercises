"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import chromadb
import pytest

from backend.settings import Settings
from backend.tools import ToolSet


@pytest.fixture
def sandbox(tmp_path: Path):
    """A temporary workspace + a fresh in-memory Chroma collection.

    Returns a ToolSet bound to the sandbox. Tests that need the tool
    implementations but not the real corpus should use this.
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sandbox\n\nThis is a test workspace.\n", encoding="utf-8")
    (workspace / "src").mkdir()
    (workspace / "src" / "hello.py").write_text("def hello(): return 'hi'\n", encoding="utf-8")

    patches = tmp_path / "patches"
    patches.mkdir()

    # Use a persistent client on a temp path; it behaves like in-memory for a
    # test since the directory is thrown away at the end.
    chroma_root = tmp_path / "chroma"
    chroma_client = chromadb.PersistentClient(path=str(chroma_root))
    collection = chroma_client.create_collection("test-corpus")
    collection.add(
        documents=[
            "Authentication uses session cookies. Sessions live in Redis.",
            "The testing pyramid has three layers: unit, integration, and e2e.",
            "Deployments run via `fly deploy --remote-only` from main.",
        ],
        metadatas=[
            {"source": "auth.md", "heading": "Sessions"},
            {"source": "testing.md", "heading": "Layers"},
            {"source": "deploy.md", "heading": "How"},
        ],
        ids=["a", "b", "c"],
    )

    tools = ToolSet(
        workspace_root=workspace,
        chroma_persist_root=chroma_root,
        chroma_collection_name="test-corpus",
        patches_root=patches,
    )

    yield {"workspace": workspace, "patches": patches, "tools": tools}


@pytest.fixture
def settings_for_test(sandbox, monkeypatch):
    """A Settings object pointing at the sandbox, with a fake API key."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-do-not-use")
    return Settings(
        anthropic_api_key="test-key",
        model="claude-sonnet-4-6",
        workspace_root=sandbox["workspace"],
        chroma_persist_root=sandbox["workspace"].parent / "chroma",
        chroma_collection_name="test-corpus",
        patches_root=sandbox["patches"],
        max_agent_turns=5,
        confidence_threshold=0.3,
    )
