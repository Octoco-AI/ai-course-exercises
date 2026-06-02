# chroma-corpora — Combo 3 M4 reference

Two pre-built Chroma indexes for the Combo 3 running artefact, one per track:

- **`track-a-codebase/`** — corpus about **TodoMagic**, a fictional todo-list microservice. Feeds the codebase-Q&A agent.
- **`track-b-helpdesk/`** — KB articles for **Streakly**, a fictional habit-tracker. Feeds the helpdesk agent.

Both use the same shared indexer and search helper (`shared/`), so attendees can compare how the same code handles two different document shapes.

## Setup (pre-workshop)

```bash
python3 -m venv .venv
source .venv/bin/activate          # or .venv\Scripts\activate on Windows
pip install -e '.[dev]'
./verify.sh                         # runs tests + builds both indexes
```

**First-run note**: the first `python build.py` downloads Chroma's default embedding model (~79 MB, one-time, cached at `~/.cache/chroma/`). If you ran `_shared/verify-eval-tools.sh` before, the cache is already warm and build is fast.

## Usage in the M4 agent

Each track's corpus exposes the same shape to an agent:

```python
from pathlib import Path
from shared.search import CorpusSearch

searcher = CorpusSearch(
    persist_root=Path("track-a-codebase/.chroma"),  # or track-b-helpdesk
    collection_name="track-a-codebase",              # matches the directory name
)

hits = searcher.search("how do I run the tests", k=5)
# hits is a list of {"text", "source", "heading", "score"} dicts,
# ready to return from an agent tool.
```

The agent's `search_docs(query)` tool wraps this — one line:

```python
@mcp.tool()  # or @tool in the Anthropic SDK
def search_docs(query: str) -> list[dict]:
    return searcher.search(query, k=5)
```

## What's here

```
chroma-corpora/
├── README.md                 ← you are here
├── FACILITATOR.md            ← notes for running M4
├── pyproject.toml
├── verify.sh                 ← pre-flight + build both indexes
├── shared/
│   ├── indexer.py            ← reusable build (chunking + upsert)
│   └── search.py             ← reusable search (Chroma → agent-shaped hits)
├── track-a-codebase/
│   ├── README.md
│   ├── docs/                 ← 8 files about TodoMagic
│   ├── build.py
│   └── search_example.py
├── track-b-helpdesk/
│   ├── README.md
│   ├── docs/                 ← 8 Streakly KB articles
│   ├── build.py
│   └── search_example.py
└── tests/
    └── test_indexer.py
```

## Principles behind the design

**Tiny and readable.** `shared/indexer.py` is ~150 lines. Attendees can read it in 5 minutes. Production indexers add proper tokenisation, chunk overlap tuning, semantic chunking — we skip those so the concept lands.

**Deterministic IDs.** Each chunk's ID is a SHA-1 of `(source, heading, first 100 chars)`. This lets `build.py` run multiple times without duplicating rows — `upsert` replaces in-place.

**Heading-aware chunking.** Markdown with `##` headings gets split cleanly on those boundaries. Fallback for flat docs is a simple sliding window. Production: swap in `langchain`, `llama_index`, or your own tokeniser-aware splitter.

**Default embedding model.** Chroma's built-in `DefaultEmbeddingFunction` is ONNX-based, runs locally, no API key. Good enough for workshop demos. Production: evaluate Voyage, OpenAI, or Cohere embeddings on your own data before committing.

**Score normalisation.** The raw distance from Chroma is cosine distance in `[0, 2]` (0 = identical). We invert and clip to a rough `[0, 1]` relevance score. Rough — use for ranking, not as a calibrated probability.

## What this corpus is NOT

- **Not a RAG tutorial.** Retrieval-augmented generation has many more pieces (re-ranking, query rewriting, hybrid search). This is the minimal "search over documents" slice needed for M4.
- **Not a benchmark.** We don't measure retrieval quality. In a real product you'd build eval sets specifically for retrieval (as distinct from generation quality).
- **Not representative of your production documents.** These are small, well-structured markdown. Real docs are messier. The pedagogy carries over; the chunking strategy may need to evolve.

## Post-workshop

Take this home. Natural next steps:

1. **Index your team's real docs.** Drop `.md` files into `docs/` and run `build.py`. The default pipeline handles most cases.
2. **Swap the embedding model.** The `DefaultEmbeddingFunction` is fine for English technical text; for other languages or specialised domains, Chroma supports OpenAI / Voyage / Cohere / HuggingFace embeddings with a one-line change.
3. **Add re-ranking.** For better quality, retrieve 20 chunks and re-rank to 5 using a cross-encoder or a small LLM. See the Inspect AI docs for agent trajectories over retrieval.
4. **Measure retrieval quality.** Build an eval set: `(query, expected_relevant_chunk_ids)`. Measure recall@k and MRR on changes to the indexer or embedding model.
