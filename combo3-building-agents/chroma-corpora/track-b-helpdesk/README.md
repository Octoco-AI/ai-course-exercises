# Track B — Helpdesk corpus

Knowledge-base articles for **Streakly**, a fictional habit-tracker app. The Combo 3 Track B running artefact is a helpdesk agent that answers user questions from this corpus and escalates to a human when appropriate.

## What's here

- `docs/` — 8 articles covering signup, billing, streaks, widgets, privacy, security, sync, and support contact. ~1,200 lines of realistic help-centre content.
- `build.py` — builds the Chroma index from `docs/`.
- `search_example.py` — quick CLI search to verify the index works.

## Build and test

```bash
# From the chroma-corpora/ root, after `pip install -e .`
cd track-b-helpdesk
python build.py

# Try queries:
python search_example.py "how do I get a refund"
python search_example.py "my widget isn't updating"
python search_example.py "I think someone is using my account"
```

## Integrating into the M4 agent

Same shape as Track A. The agent's `search_docs(query)` tool wraps `CorpusSearch`:

```python
from shared.search import CorpusSearch

_searcher = CorpusSearch(
    persist_root=Path("track-b-helpdesk/.chroma"),
    collection_name="track-b-helpdesk",
)
```

The agent is additionally expected to know the escalation rules from `docs/README.md` ("When the agent should escalate to a human") — those aren't just corpus content but part of the agent's system prompt.

## Typical queries the agent handles well

- "How do I enable 2FA?" → account-security.md
- "I was charged twice." → billing-and-plans.md (plus escalation prompt)
- "Why did my streak reset?" → streaks-and-tracking.md
- "My notifications aren't working." → widgets-and-notifications.md
- "How do I export my data?" → data-and-privacy.md
- "Sync isn't working between my phone and tablet." → troubleshooting-sync.md

## Queries that should trigger escalation

- "I can't access my email and I've lost my 2FA device." → account recovery, high-risk
- "You charged me $49 and I don't have Plus." → billing dispute (over $20)
- "I think my child's account was created without my permission." → legal review
- "Your app is garbage and I want a refund." → frustrated tone, likely escalate

## Queries the agent should politely decline

- "What's my current streak?" — we can't see a specific user's data.
- "Delete my account for me." — must be done from the app.
- "Can you cancel Plus for me?" — Apple/Google only.

These should trigger a clear "here's how to do it yourself" response, with links if possible.
