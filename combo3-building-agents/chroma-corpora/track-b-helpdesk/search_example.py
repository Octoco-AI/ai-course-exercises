"""Search the Track B corpus and print results.

Usage:
    python search_example.py "<your query>"
    python search_example.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from shared.search import CorpusSearch


HERE = Path(__file__).parent
PERSIST_ROOT = HERE / ".chroma"
COLLECTION_NAME = "track-b-helpdesk"

DEFAULT_QUERY = "My streak disappeared after travelling. What happened?"


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
        preview = hit["text"].replace("\n", " ")[:200]
        print(f"  {preview}{'...' if len(hit['text']) > 200 else ''}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
