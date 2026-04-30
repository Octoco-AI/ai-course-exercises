"""Search the Track A corpus and print results — the shape an agent tool would use.

Usage:
    python search_example.py "<your query>"
    python search_example.py               # uses a canned query
"""

from __future__ import annotations

import sys
from pathlib import Path

from shared.search import CorpusSearch


HERE = Path(__file__).parent
PERSIST_ROOT = HERE / ".chroma"
COLLECTION_NAME = "track-a-codebase"

DEFAULT_QUERY = "How do I authenticate a user in this service?"


def main() -> int:
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_QUERY
    print(f"Query: {query}\n")

    searcher = CorpusSearch(persist_root=PERSIST_ROOT, collection_name=COLLECTION_NAME)
    hits = searcher.search(query, k=3)

    for i, hit in enumerate(hits, start=1):
        print(f"─── Hit {i} (score={hit['score']:.3f}) ───")
        print(f"  source:  {hit['source']}")
        if hit["heading"]:
            print(f"  heading: {hit['heading']}")
        print()
        # Show just the first 200 chars of the chunk for readability.
        preview = hit["text"].replace("\n", " ")[:200]
        print(f"  {preview}{'...' if len(hit['text']) > 200 else ''}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
