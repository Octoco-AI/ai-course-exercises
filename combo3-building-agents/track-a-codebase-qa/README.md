# Track A — Codebase Q&A (Combo 3 running artefact)

A streaming agent that answers questions about a codebase and drafts small changes as patch files. Full stack: **Anthropic Claude** backend loop, **FastAPI** streaming endpoint, **React + Vite** chat UI, **Chroma** retrieval, runs in **Docker**.

This is the running thread across Combo 3 modules M1 through M11. Each module adds one slice:

| Module | Slice this artefact demonstrates |
|---|---|
| M1 — Agent loop | `backend/agent.py` — the loop, dispatching tools, termination on no-tool-use |
| M2 — Tool design | `backend/tools.py` + `anthropic_tool_schemas()` — 4 tools, all sandboxed |
| M3a — Streaming backend | `backend/streaming.py` + SSE endpoint in `backend/server.py` |
| M3b — Chat UI | `ui/src/hooks/useStreamingChat.ts` + components |
| M4 — Context engineering | `search_docs` tool wrapping `../chroma-corpora/track-a-codebase/` |
| M5 — MCP | (see `../mcp-server/` — wrap these same tools as MCP) |
| M6 — Caching | `backend/agent.py` — system prompt is stable across turns (candidate for prompt caching; see M6 notes) |
| M7 — Evals | `tests/test_agent.py` + the eval extension path documented below |
| M8 — Tracing | Opik integration point in `backend/agent.py` (see M8 notes) |
| M9 — Guardrails | `backend/guardrails.py` + `draft_patch` stubbed PR |
| M11 — Deployment | `Dockerfile` + `docker-compose.yml` |

---

## Setup

```bash
# 1. Python side
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env   # then edit .env and add your Anthropic key

# 2. Seed the workspace with the TodoMagic docs (source of truth the agent reads)
./scripts/seed-workspace.sh

# 3. Build the Chroma index (once; cached after)
(cd ../chroma-corpora/track-a-codebase && python build.py)

# 4. UI side (required for the browser chat; skip if you're using curl only)
cd ui && npm install && npm run build && cd ..

# 5. Verify everything
./verify.sh
```

---

## Running

### Local (for development)

Two terminals:

```bash
# Terminal 1 — backend
track-a-server
# or: uvicorn backend.server:app --reload
```

```bash
# Terminal 2 — UI (Vite dev server with proxy to backend)
cd ui && npm run dev
```

Open http://localhost:5173.

### Local (single process, UI served from backend)

Build the UI bundle first:

```bash
cd ui && npm run build && cd ..
track-a-server
```

Open http://localhost:8000.

### Docker

```bash
docker compose up --build
```

Open http://localhost:8000. The container mounts:
- `./workspace/` at `/app/workspace` (read/draft)
- `./patches/` at `/app/patches` (persistent)
- `../chroma-corpora/track-a-codebase/.chroma/` at `/app/chroma-index` (read-only)

### curl (no UI)

```bash
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How does authentication work in TodoMagic?"}'
```

The `-N` disables curl's output buffering so you see the stream in real time.

---

## The four tools

| Tool | Purpose | Blocks |
|---|---|---|
| `search_docs(query)` | Find passages in the Chroma corpus about TodoMagic | — |
| `read_file(path)` | Read a file from `workspace/` | sandboxed — can't escape |
| `list_files(path)` | List a directory in `workspace/` | sandboxed |
| `draft_patch(path, old_str, new_str)` | Write a unified-diff to `patches/`. **Never modifies the workspace.** | old_str must appear exactly once |

### Why stubbed PRs and not actual edits

The Combo 3 M9 guardrails module explicitly calls for this pattern: the agent proposes, a human disposes. A drafted patch is:

1. A file under `patches/` with a timestamp in the name.
2. A standard unified diff, applyable with `patch -p1 < patches/<name>.patch`.
3. An invitation for human review, not a completed action.

No git integration. No pushes. No destructive operations. See `backend/guardrails.py` for the full forbidden-actions list.

---

## Example prompts (to try)

Exploration:
- *"What tools does the agent have?"*
- *"List the files in the workspace."*
- *"How does the testing pyramid work in TodoMagic?"*

Understanding:
- *"How does authentication work?"*
- *"What does the service do when the database is slow?"*
- *"Walk me through the deploy process."*

Patch drafting:
- *"Draft a patch that adds a 'Last updated' line at the top of README.md."*
- *"Propose adding a migration for a `users.display_name` column. Give me the migration file contents as a patch."*
- *"Find the session TTL and draft a change to make it configurable via env."*

Escalation (agent should gracefully decline):
- *"Delete the session-expiry logic."* → declines; offers a patch that comments it out instead.
- *"Push this change to main."* → declines; explains the draft-only scope.
- *"Send an email to the team about this."* → declines; no email tool.

---

## How each Combo 3 module extends this

### M6 — Prompt caching

The system prompt and tool schemas are stable across turns. Add prompt caching by passing `cache_control: {"type": "ephemeral"}` on the system prompt block in `backend/agent.py`. For the workshop, demonstrate with the Anthropic SDK's native caching; measure before/after `cache_read_input_tokens` in the response `usage`.

### M7 — Evals

`tests/test_agent.py` is the scaffolding. For real evals against the live agent:
1. Build a golden dataset of `(prompt, expected_behaviour)` cases.
2. Three layers of gate:
   - **Tool-use correctness**: did the agent call the right tools in the right order? Assert on the sequence of `tool_call` events.
   - **Task success**: LLM-as-judge grades the final text against the expected answer.
   - **Catastrophic failure**: no forbidden actions, no workspace mutations.
3. Wire into CI as a `pytest -m evals` job with `ANTHROPIC_API_KEY` secret.

See Combo 2 M5's `expense-categoriser` sample for the CI pattern to copy.

### M8 — Tracing (Opik)

Instrument `run_agent_streaming` with `@opik.track` (see `../../../_shared/eval-tooling-install.md`). Every LLM call and every tool dispatch becomes a span, grouped by session. Add `session.id` to the trace attributes so the dashboard groups multi-turn conversations.

### M10 — Extended thinking

Opus 4.7 supports adaptive thinking. In `backend/agent.py`, add:

```python
with client.messages.stream(
    model="claude-opus-4-7",
    thinking={"type": "adaptive", "effort": "high"},
    ...
)
```

**Gotcha**: extended thinking is incompatible with `tool_choice: "any"`. The agent uses the default (`"auto"`), so this works as-is.

### M11 — Deployment patterns

The supplied `Dockerfile` + `docker-compose.yml` is the local Docker sandbox. For managed runtimes (AgentCore et al.), see Herman's *"Building production agents on AgentCore"* — the 6 services, the entrypoint pattern, the three observability traps. Not hands-on in the workshop; conceptual only.

---

## File map

```
track-a-codebase-qa/
├── backend/
│   ├── settings.py       ← env + defaults
│   ├── guardrails.py     ← path sandbox + forbidden-actions list
│   ├── tools.py          ← 4 tool methods + Anthropic schemas
│   ├── streaming.py      ← SSE event shaping
│   ├── agent.py          ← the streaming loop
│   └── server.py         ← FastAPI app
├── ui/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── hooks/useStreamingChat.ts   ← THE pedagogical piece
│       ├── components/{ChatPanel,Message,ToolCallBlock,InputBar}.tsx
│       └── styles.css
├── workspace/            ← what the agent reads (seeded from chroma-corpora)
├── patches/              ← where draft_patch writes
├── tests/
│   ├── conftest.py
│   ├── test_tools.py
│   ├── test_guardrails.py
│   ├── test_agent.py     ← mocked Anthropic; full-loop test
│   └── test_api.py
├── scripts/
│   └── seed-workspace.sh
├── Dockerfile
├── docker-compose.yml
├── verify.sh
├── pyproject.toml
├── .env.example
└── .gitignore
```

---

## What this running artefact is NOT

- **Not production-ready.** No auth. No rate limiting. No per-user workspace isolation.
- **Not the only way.** You could use Gemini instead of Anthropic (mirror Combo 1 M1), the Vercel AI SDK instead of raw SSE (1-day variant), Pinecone instead of Chroma. The shapes stay the same.
- **Not a LangChain tutorial.** No frameworks on the agent side. The loop is 100 lines of Python.
- **Not complete.** Track B (the helpdesk agent) uses the same backend shape but with different tools, different system prompt, different eval strategy. See `../track-b-helpdesk-qa/` once that lands.
