# Track A — Codebase Q&A corpus

Documents about **TodoMagic**, a fictional todo-list microservice. The Combo 3 Track A running artefact is an agent that answers developer questions about this code using this corpus.

## What's here

- `docs/` — README, architecture, API, testing, deployment, changelog, a runbook, and contributing guide. 8 files, ~1,500 lines total.
- `build.py` — builds the Chroma index from `docs/`.
- `search_example.py` — quick CLI search to verify the index works.

## Build and test

```bash
# From the chroma-corpora/ root, after `pip install -e .`
cd track-a-codebase
python build.py

# Try a few queries:
python search_example.py "how do sessions work"
python search_example.py "what happens on deploy"
python search_example.py "can I refund a user"
```

(That last one should return low-relevance hits — it's a Track B kind of question. Useful for showing what "irrelevant" looks like in the score.)

## Integrating into the M4 agent

Your agent's `search_docs(query)` tool wraps the `CorpusSearch` class:

```python
from shared.search import CorpusSearch

_searcher = CorpusSearch(
    persist_root=Path("track-a-codebase/.chroma"),
    collection_name="track-a-codebase",
)

def search_docs(query: str) -> list[dict]:
    """Return up to 5 relevant chunks from the TodoMagic docs."""
    return _searcher.search(query, k=5)
```

That's it. The agent reads the hits and cites them by `source` and `heading`.

## Typical queries the agent should handle well

- "How do I set up the local dev environment?" → contributing.md
- "What database does this service use?" → architecture.md, README.md
- "What's the endpoint for logging in?" → api.md
- "What's changed in the last few releases?" → changelog.md
- "How do I run the integration tests?" → testing.md
- "What do I do if auth is broken?" → runbook-auth-outage.md
- "Can I push directly to main?" → contributing.md

## Typical queries the agent should escalate or apologise for

- "What's Alice's email?" — not in the corpus; we don't know.
- "Delete my account." — the service doesn't expose that; we don't do anything destructive here.
- Anything requiring live data ("what's the current traffic?") — the agent can't answer.
