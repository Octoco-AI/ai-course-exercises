# Track A — Codebase Q&A (Combo 5 Day-3 starter)

A streaming agent that answers questions about a codebase and drafts small
changes as patch files. Full stack once built: **Gemini** (default) or
**Anthropic** backend loop, **FastAPI** streaming endpoint, **React + Vite**
chat UI, **Chroma** retrieval (Module 13+), runs in **Docker**.

**This is a starter, not a finished app.** `backend/agent.py` and
`backend/tools.py` are stubs with `TODO` comments — you write the async
agent loop and its tools yourself across Module 11, then wrap it in a
streaming chat UI in Module 12. This repo is the running thread across
Modules 11 through 19. Each module adds one slice:

| Module | Slice this artefact demonstrates |
|---|---|
| M11 — Agent loop + tool design | `backend/agent.py`, `backend/tools.py` — the loop, three tools, error-as-string dispatch |
| M12 — Streaming + chat UI | `backend/streaming.py` + SSE endpoint in `backend/server.py`; `ui/src/hooks/useStreamingChat.ts` + `ToolCallBlock.tsx` |
| M13 — Memory & retrieval | `search_docs` tool wrapping `../chroma-corpora/track-a-codebase/` |
| M14 — MCP | (see `../mcp-server/` — wrap your tools as MCP) |
| M15 — Caching | Context caching on the stable system prompt + tool schemas |
| M16 — Evals for agents | `tests/evals/` — you build this from scratch |
| M17 — Tracing | Opik integration point in `backend/agent.py` |
| M18 — Guardrails | `backend/guardrails.py` deepened; `edit_file` → `draft_patch` |
| M19 — Reasoning models | Model/thinking-budget routing in `backend/agent.py` |

Fell behind, or want to see a module's end state? See **Catching up**, below.

---

## Setup

```bash
# 1. Python side
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env   # then edit .env and add your Gemini key (default) or Anthropic key

# 2. Seed the workspace with the TodoMagic docs + sample code
./scripts/seed-workspace.sh

# 3. UI side (required for the browser chat in Module 12; skip if using curl/run_agent.py only)
cd ui && npm install && cd ..

# 4. Verify everything
./verify.sh
```

`./verify.sh` is green on a fresh clone — Module 11/12 tests are designed
to *skip* (not fail) until you've implemented the step they check. Run
`pytest -m m11` / `pytest -m m12` to check your own progress.

---

## Working the exercise

Until Module 12 wires up the FastAPI endpoint, talk to the agent via the
CLI:

```bash
python run_agent.py "What files exist in the workspace?"
python run_agent.py --stream "What files exist in the workspace?"   # after Module 12
```

Once Module 12 is done:

```bash
# Terminal 1 — backend
track-a-server                          # or: uvicorn backend.server:app --reload
# Terminal 2 — UI (Vite dev server with proxy to backend)
cd ui && npm run dev
```

Open http://localhost:5173.

### Docker (Module 19+ / deployment discussion)

```bash
docker compose up --build
```

Open http://localhost:8000. The container mounts `./workspace/` (read/draft),
`./patches/` (persistent), and the Chroma index (read-only).

---

## Catching up

Every attendee works in the same `backend/`/`ui/` tree across the whole
arc — there's no separate "starter" per module, just this one repo at
increasing states of completion. Two ways to fast-forward if you fall
behind or want to see a worked example:

```bash
./scripts/checkpoint.sh m11-end   # overlays the Module 11 end state — sets you up for Module 12
./scripts/checkpoint.sh m12-end   # overlays the Module 12 end state — sets you up for Module 13
```

This **overwrites** the files the checkpoint provides. Commit or stash
first if you want to keep your own attempt.

`reference/` is a full, browsable copy of the Module 12 end state (same
content as `checkpoints/m12-end/`, laid out as a complete tree instead of
an overlay) — useful for reading end-to-end without touching your working
copy. It's not wired into the live package; see `reference/REFERENCE.md`.

---

## The tools, by the time you're through Module 18

| Tool | Purpose | Arrives |
|---|---|---|
| `read_file(path)` | Read a file from `workspace/` | Module 11 |
| `list_files(path)` | List a directory in `workspace/` | Module 11 |
| `edit_file(path, old_str, new_str)` → `draft_patch(...)` | Mutate a file in place; Module 18 converts this to a non-mutating diff writer | Module 11, converted Module 18 |
| `search_docs(query)` | Find passages in the Chroma corpus | Module 13 |

All four are sandboxed to `workspace/` via `backend/guardrails.py`'s
`ensure_within` — the agent cannot escape, even if the model asks.

### Why `draft_patch` and not a real edit (Module 18)

Module 18's guardrails module has you convert `edit_file` into
`draft_patch`: same signature, but instead of writing the replacement in
place it computes a unified diff and writes it to `patches/`. The
workspace is never touched — a human reviews the patch and applies it out
of band with `patch -p1 < patches/<name>.patch`. No git integration, no
pushes. See `backend/guardrails.py` for the full forbidden-actions list.

---

## Example prompts (to try from Module 11 on)

Exploration:
- *"What files exist in the workspace?"*
- *"What does this codebase do? Summarise in 3 sentences."*

Bug fix (the Module 11 moment):
- *"Find and fix the bug in src/math_utils.py."*

Error recovery:
- *"Read the file at /etc/passwd"* → declines; explains the sandbox.
- *"Read README.tx (note typo) and summarise it."* (Module 11, Step 9)

Once `search_docs` and `draft_patch` exist (Modules 13 and 18):
- *"How does authentication work?"*
- *"Draft a patch that adds a 'Last updated' line at the top of README.md."*
- *"Delete the session-expiry logic."* → declines; offers a patch that comments it out instead.

---

## File map

```
track-a-codebase-qa/
├── backend/
│   ├── settings.py       ← given: env + defaults
│   ├── guardrails.py     ← given: path sandbox + forbidden-actions list
│   ├── tools.py          ← YOU WRITE (Module 11): Tool/ToolSet + handlers
│   ├── agent.py          ← YOU WRITE (Module 11 loop, Module 12 streaming)
│   └── server.py         ← YOU WRITE (Module 12): /api/chat SSE endpoint
├── run_agent.py           ← given: CLI entry point
├── ui/src/
│   ├── App.tsx, main.tsx, styles.css              ← given
│   ├── components/{ChatPanel,Message,InputBar}.tsx ← given
│   ├── components/ToolCallBlock.tsx                ← YOU WRITE (Module 12)
│   └── hooks/useStreamingChat.ts                   ← YOU WRITE (Module 12)
├── sample_code/          ← seeded into workspace/src/ (has the M11 bug)
├── workspace/            ← what the agent reads (seeded — don't hand-edit)
├── patches/              ← where draft_patch writes (Module 18+)
├── checkpoints/          ← catch-up snapshots (m11-end, m12-end)
├── reference/            ← full browsable copy of the Module 12 end state
├── tests/
│   ├── test_scaffold.py  ← always green
│   ├── m11/               ← pytest -m m11
│   └── m12/               ← pytest -m m12
├── scripts/
│   ├── seed-workspace.sh
│   ├── checkpoint.sh
│   └── test-reference.sh ← facilitator-only
├── Dockerfile, docker-compose.yml
├── verify.sh
├── pyproject.toml
├── .env.example
└── .gitignore
```

---

## What this running artefact is NOT

- **Not production-ready.** No auth. No rate limiting. No per-user workspace isolation.
- **Not the only way.** You could build on Anthropic instead of Gemini (`LLM_PROVIDER=anthropic`), the Vercel AI SDK instead of raw SSE (1-day variant), Pinecone instead of Chroma. The shapes stay the same.
- **Not a LangChain tutorial.** No frameworks on the agent side. The loop is well under 100 lines of Python.
- **Not the only track.** Track B (the helpdesk agent) uses the same backend shape but with different tools, a different system prompt, different eval strategy. See `../track-b-helpdesk-qa/`.
