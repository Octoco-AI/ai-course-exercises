"""Module 13 — search_docs over the Chroma corpus.

Skips at module level until `search_docs` exists on `backend.tools` — the
expected state through Module 12. These tests don't need the real
chroma-corpora index built: the fixture below builds its own tiny
throwaway Chroma collection in tmp_path.

Run just these with: pytest -m m13 tests/m13/test_tools.py
"""

from __future__ import annotations

from pathlib import Path

import chromadb
import pytest

from backend import tools as tools_module

if not hasattr(tools_module, "search_docs"):
    pytest.skip("search_docs not implemented yet — Module 13.", allow_module_level=True)

pytestmark = pytest.mark.m13

COLLECTION_NAME = "test-docs"


@pytest.fixture
def chroma_index(tmp_path: Path) -> Path:
    """A tiny throwaway Chroma index — not the real chroma-corpora one."""
    persist_root = tmp_path / ".chroma"
    client = chromadb.PersistentClient(path=str(persist_root))
    collection = client.get_or_create_collection(COLLECTION_NAME)
    collection.upsert(
        ids=["1", "2"],
        documents=[
            "Authentication uses session cookies set on POST /auth/login.",
            "Deployment runs on Fly.io, single region, via `fly deploy`.",
        ],
        metadatas=[
            {"source": "api.md", "heading": "Auth"},
            {"source": "deployment.md", "heading": "Where"},
        ],
    )
    return persist_root


@pytest.fixture
def tools_with_index(chroma_index: Path):
    from backend.tools import build_toolset

    workspace = chroma_index.parent / "workspace"
    workspace.mkdir()
    return build_toolset(
        workspace,
        chroma_persist_root=chroma_index,
        chroma_collection_name=COLLECTION_NAME,
    )


def test_search_docs_returns_relevant_hit(tools_with_index):
    result = tools_with_index.dispatch("search_docs", {"query": "how does login work", "k": 2})
    assert "api.md" in result


def test_search_docs_ranks_relevant_hit_first(tools_with_index):
    import json

    hits = json.loads(tools_with_index.dispatch("search_docs", {"query": "how does login work", "k": 2}))
    assert hits[0]["source"] == "api.md"
    assert hits[0]["score"] > hits[1]["score"]


def test_search_docs_missing_index_returns_error_string(tmp_path: Path):
    from backend.tools import build_toolset

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    tools = build_toolset(
        workspace,
        chroma_persist_root=tmp_path / "does-not-exist",
        chroma_collection_name="nope",
    )
    result = tools.dispatch("search_docs", {"query": "anything"})
    assert result.startswith("ERROR:")


def test_build_toolset_defaults_chroma_settings_when_omitted(tmp_path: Path):
    """Backward compatible: run_agent.py calls build_toolset(workspace) with
    no chroma args at all — it must still register search_docs."""
    from backend.tools import build_toolset

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    tools = build_toolset(workspace)
    assert "search_docs" in [t["name"] for t in tools.schemas()]
