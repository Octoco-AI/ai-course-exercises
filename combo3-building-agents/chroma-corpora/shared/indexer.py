"""Reusable indexer.

Walks a directory of markdown / text documents, chunks each file by headings
(falling back to line-windowed chunking for files without headings), and
upserts to a Chroma collection.

Deliberately kept minimal — ~100 lines — so attendees in Combo 3 M4 can read
it end-to-end. Production indexers add proper tokenisation, overlap, and
semantic chunking; we skip those for clarity.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import chromadb
from chromadb import Collection


# How big a chunk we aim for when a document has no headings. In characters;
# we don't pull in a tokeniser here to keep the dep tree tiny.
TARGET_CHUNK_CHARS = 1200
CHUNK_OVERLAP_CHARS = 150


@dataclass(frozen=True)
class Chunk:
    """One indexable unit."""

    id: str
    text: str
    source: str          # file path relative to docs-root, for citation
    heading: str | None  # heading this chunk lives under, if any


def chunk_document(path: Path, docs_root: Path) -> list[Chunk]:
    """Chunk one file.

    Strategy: split on H2 headings (## ...). A document without H2s is
    chunked as a sliding window over its text. Both strategies produce
    chunks roughly ~TARGET_CHUNK_CHARS in size.
    """
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    rel = str(path.relative_to(docs_root))

    # Try heading-based split.
    heading_pattern = re.compile(r"^##\s+(.*?)$", re.MULTILINE)
    matches = list(heading_pattern.finditer(text))

    if matches:
        chunks: list[Chunk] = []
        # Preamble (text before the first ## heading).
        first_start = matches[0].start()
        if first_start > 0:
            preamble = text[:first_start].strip()
            if preamble:
                chunks.append(_make_chunk(preamble, rel, heading=None))
        # Each ##-bounded section becomes one chunk.
        for i, m in enumerate(matches):
            section_start = m.start()
            section_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            heading = m.group(1).strip()
            body = text[section_start:section_end].strip()
            chunks.append(_make_chunk(body, rel, heading=heading))
        # Sections that are too big get sliced further.
        return _split_large_chunks(chunks)

    # No headings: sliding-window over the whole doc.
    return _window_chunks(text, rel)


def _make_chunk(body: str, source: str, heading: str | None) -> Chunk:
    chunk_id = hashlib.sha1(f"{source}::{heading}::{body[:100]}".encode()).hexdigest()[:16]
    return Chunk(id=chunk_id, text=body, source=source, heading=heading)


def _split_large_chunks(chunks: list[Chunk]) -> list[Chunk]:
    result: list[Chunk] = []
    for chunk in chunks:
        if len(chunk.text) <= TARGET_CHUNK_CHARS * 1.5:
            result.append(chunk)
            continue
        # Break on paragraph boundaries.
        paragraphs = chunk.text.split("\n\n")
        buffer: list[str] = []
        buffer_len = 0
        for p in paragraphs:
            if buffer_len + len(p) > TARGET_CHUNK_CHARS and buffer:
                joined = "\n\n".join(buffer)
                result.append(_make_chunk(joined, chunk.source, chunk.heading))
                buffer = [p]
                buffer_len = len(p)
            else:
                buffer.append(p)
                buffer_len += len(p)
        if buffer:
            joined = "\n\n".join(buffer)
            result.append(_make_chunk(joined, chunk.source, chunk.heading))
    return result


def _window_chunks(text: str, source: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    step = TARGET_CHUNK_CHARS - CHUNK_OVERLAP_CHARS
    for start in range(0, len(text), step):
        end = min(start + TARGET_CHUNK_CHARS, len(text))
        body = text[start:end].strip()
        if body:
            chunks.append(_make_chunk(body, source, heading=None))
        if end == len(text):
            break
    return chunks


def build_index(
    docs_root: Path,
    persist_root: Path,
    collection_name: str,
    *,
    extensions: tuple[str, ...] = (".md", ".txt"),
    reset: bool = True,
) -> Collection:
    """Build a Chroma index from a directory of text documents.

    Args:
        docs_root: Directory to walk. Every matching file becomes chunks.
        persist_root: Directory Chroma persists to. Created if absent.
        collection_name: Name for the Chroma collection.
        extensions: File extensions to include.
        reset: If True (default), delete any existing collection first so the
            build is reproducible.

    Returns:
        The built collection.
    """
    persist_root.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_root))

    if reset:
        try:
            client.delete_collection(collection_name)
        except Exception:  # noqa: BLE001 — collection may not exist yet
            pass

    collection = client.get_or_create_collection(collection_name)

    all_chunks: list[Chunk] = []
    for path in sorted(docs_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue
        all_chunks.extend(chunk_document(path, docs_root))

    if not all_chunks:
        raise RuntimeError(f"No indexable files found in {docs_root}")

    collection.upsert(
        ids=[c.id for c in all_chunks],
        documents=[c.text for c in all_chunks],
        metadatas=[
            {"source": c.source, "heading": c.heading or ""}
            for c in all_chunks
        ],
    )

    return collection
