"""Search helper — the shape an agent tool actually uses.

Wrap an existing Chroma collection and expose `search(query, k)` that returns
a list of dicts ready to be serialised into a tool response. This is the
interface the agent in Combo 3 M4 talks to.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

import chromadb


class SearchHit(TypedDict):
    """One search result, shaped for the agent to consume."""

    text: str
    source: str
    heading: str
    score: float  # 0.0 = irrelevant, 1.0 = exact match (inverted from Chroma's distance)


class CorpusSearch:
    """Thin wrapper around a persisted Chroma collection."""

    def __init__(self, persist_root: Path, collection_name: str) -> None:
        if not persist_root.exists():
            raise FileNotFoundError(
                f"Chroma index not found at {persist_root}. Run `python build.py` first."
            )
        client = chromadb.PersistentClient(path=str(persist_root))
        self.collection = client.get_collection(collection_name)

    def search(self, query: str, k: int = 5) -> list[SearchHit]:
        """Return up to k most-relevant chunks for the query.

        Scores are a rough "relevance" in [0, 1]: 1.0 ≈ very relevant,
        near 0 ≈ unrelated. Derived from Chroma's distance; the scale
        varies by embedding model but is monotonic — useful for ranking
        and for "drop hits below threshold" behaviour in the agent.
        """
        result = self.collection.query(
            query_texts=[query],
            n_results=k,
        )

        hits: list[SearchHit] = []
        docs = result["documents"][0]
        metadatas = result["metadatas"][0]
        distances = result["distances"][0] if result.get("distances") else [None] * len(docs)

        for doc, meta, dist in zip(docs, metadatas, distances):
            # Chroma's default cosine distance is in [0, 2]; 0 is identical.
            # Invert and clip so higher = more relevant, suitable for agent
            # ranking. This is a rough heuristic, not a calibrated probability.
            score = max(0.0, 1.0 - float(dist) / 2.0) if dist is not None else 0.0
            hits.append({
                "text": doc,
                "source": meta.get("source", ""),
                "heading": meta.get("heading", ""),
                "score": round(score, 3),
            })
        return hits

    def count(self) -> int:
        """Number of chunks in the collection."""
        return self.collection.count()
