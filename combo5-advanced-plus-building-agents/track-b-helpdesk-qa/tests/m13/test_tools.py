"""Module 13 — search_kb over the Chroma corpus.

Skips at module level until `search_kb` exists on `backend.tools` — the
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

if not hasattr(tools_module, "search_kb"):
    pytest.skip("search_kb not implemented yet — Module 13.", allow_module_level=True)

pytestmark = pytest.mark.m13

COLLECTION_NAME = "test-kb"


@pytest.fixture
def chroma_index(tmp_path: Path) -> Path:
    """A tiny throwaway Chroma index — not the real chroma-corpora one."""
    persist_root = tmp_path / ".chroma"
    client = chromadb.PersistentClient(path=str(persist_root))
    collection = client.get_or_create_collection(COLLECTION_NAME)
    collection.upsert(
        ids=["1", "2"],
        documents=[
            "Enable two-factor authentication from Settings > Security.",
            "Refunds over $20 require manual review by a human.",
        ],
        metadatas=[
            {"source": "account-security.md", "heading": "2FA"},
            {"source": "billing-and-plans.md", "heading": "Refunds"},
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


def test_search_kb_returns_relevant_hit(tools_with_index):
    result = tools_with_index.dispatch("search_kb", {"query": "how do I turn on 2FA", "k": 2})
    assert "account-security.md" in result


def test_search_kb_ranks_relevant_hit_first(tools_with_index):
    import json

    hits = json.loads(tools_with_index.dispatch("search_kb", {"query": "how do I turn on 2FA", "k": 2}))
    assert hits[0]["source"] == "account-security.md"
    assert hits[0]["score"] > hits[1]["score"]


def test_search_kb_missing_index_returns_error_string(tmp_path: Path):
    from backend.tools import build_toolset

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    tools = build_toolset(
        workspace,
        chroma_persist_root=tmp_path / "does-not-exist",
        chroma_collection_name="nope",
    )
    result = tools.dispatch("search_kb", {"query": "anything"})
    assert result.startswith("ERROR:")


def test_build_toolset_defaults_chroma_settings_when_omitted(tmp_path: Path):
    """Backward compatible: run_agent.py calls build_toolset(workspace,
    draft_replies=...) with no chroma args at all — it must still register
    search_kb."""
    from backend.tools import build_toolset

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    tools = build_toolset(workspace, draft_replies=tmp_path / "draft-replies")
    assert "search_kb" in [t["name"] for t in tools.schemas()]
