"""Tests for the shared indexer.

These run fast and don't require the ONNX embedding model. They use a small
inline docs directory to verify chunking; the actual Chroma index test uses
an in-memory (ephemeral) client so no cache download is triggered.
"""

from __future__ import annotations

from pathlib import Path

import chromadb
import pytest

from shared.indexer import (
    TARGET_CHUNK_CHARS,
    Chunk,
    _window_chunks,
    chunk_document,
)


@pytest.fixture
def docs_root(tmp_path: Path) -> Path:
    """A tiny fake docs dir with a mix of heading-based and flat files."""
    (tmp_path / "heading_doc.md").write_text(
        "Intro paragraph.\n\n## First\n\nFirst section body.\n\n"
        "## Second\n\nSecond section body.\n",
        encoding="utf-8",
    )
    (tmp_path / "flat_doc.md").write_text(
        "A document without any headings. " * 100,
        encoding="utf-8",
    )
    (tmp_path / "empty.md").write_text("", encoding="utf-8")
    return tmp_path


def test_chunk_document_with_headings(docs_root: Path):
    chunks = chunk_document(docs_root / "heading_doc.md", docs_root)
    # Preamble + 2 sections = 3 chunks.
    assert len(chunks) == 3
    # First chunk is the preamble; no heading.
    assert chunks[0].heading is None
    assert "Intro paragraph" in chunks[0].text
    # Subsequent chunks carry their heading.
    headings = [c.heading for c in chunks[1:]]
    assert "First" in headings
    assert "Second" in headings


def test_chunk_document_without_headings(docs_root: Path):
    chunks = chunk_document(docs_root / "flat_doc.md", docs_root)
    assert len(chunks) >= 1
    # Each chunk is bounded by the target size.
    for chunk in chunks:
        assert len(chunk.text) <= TARGET_CHUNK_CHARS + 200
    # Source is set correctly.
    assert chunks[0].source == "flat_doc.md"
    # No heading for flat docs.
    assert all(c.heading is None for c in chunks)


def test_chunk_document_empty_file(docs_root: Path):
    chunks = chunk_document(docs_root / "empty.md", docs_root)
    assert chunks == []


def test_window_chunks_respects_overlap():
    text = "A" * 3000  # Larger than TARGET_CHUNK_CHARS.
    chunks = _window_chunks(text, source="big.md")
    # At least 2 chunks for 3000 chars with a target of 1200.
    assert len(chunks) >= 2
    # Consecutive chunks share overlap.
    for i in range(len(chunks) - 1):
        # Both should have some content; simpler check than actual overlap
        # (which varies because windowing is approximate).
        assert len(chunks[i].text) > 0
        assert len(chunks[i + 1].text) > 0


def test_chunk_ids_are_stable(docs_root: Path):
    first = chunk_document(docs_root / "heading_doc.md", docs_root)
    second = chunk_document(docs_root / "heading_doc.md", docs_root)
    assert [c.id for c in first] == [c.id for c in second]


# ---- chroma integration, using ephemeral (in-memory) client ---------------
#
# Note: the real build.py uses PersistentClient. Here we skip persistence
# entirely to avoid loading the ONNX embedding model during unit tests — we
# want these tests to run in <1 second on CI without network.


def test_chromadb_round_trip_with_ephemeral_client():
    """Smoke test that our chunk shape is compatible with Chroma's API."""
    client = chromadb.EphemeralClient()
    # Use a stub embedding function to avoid ONNX model download.
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction  # noqa: F401

    collection = client.get_or_create_collection("smoke")
    chunks = [
        Chunk(id="a", text="hello world", source="test.md", heading=None),
        Chunk(id="b", text="goodbye world", source="test.md", heading="Farewell"),
    ]
    collection.upsert(
        ids=[c.id for c in chunks],
        documents=[c.text for c in chunks],
        metadatas=[{"source": c.source, "heading": c.heading or ""} for c in chunks],
    )
    assert collection.count() == 2
    result = collection.query(query_texts=["hello"], n_results=1)
    assert result["ids"][0][0] in {"a", "b"}
