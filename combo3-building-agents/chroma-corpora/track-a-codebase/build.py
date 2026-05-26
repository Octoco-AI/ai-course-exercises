"""Build the Track A (codebase-Q&A) Chroma index.

Usage:
    python build.py
"""

from __future__ import annotations

import time
from pathlib import Path

from shared.indexer import build_index


HERE = Path(__file__).parent
DOCS_ROOT = HERE / "docs"
PERSIST_ROOT = HERE / ".chroma"
COLLECTION_NAME = "track-a-codebase"


def main() -> None:
    print(f"Building index from: {DOCS_ROOT}")
    print(f"Persisting to:        {PERSIST_ROOT}")
    print(f"Collection name:      {COLLECTION_NAME}")
    print()

    start = time.perf_counter()
    collection = build_index(
        docs_root=DOCS_ROOT,
        persist_root=PERSIST_ROOT,
        collection_name=COLLECTION_NAME,
    )
    elapsed = time.perf_counter() - start

    count = collection.count()
    print(f"✅ Indexed {count} chunks in {elapsed:.1f}s")
    print()
    print("Try a search:")
    print("   python search_example.py")


if __name__ == "__main__":
    main()
