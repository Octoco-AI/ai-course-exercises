# Track B — Helpdesk agent (Combo 5 Day-3 starter)

A streaming agent that triages support tickets for Streakly (a fictional
habit-tracker app): answers questions using the KB, drafts replies for a
human to send, and escalates when it can't. Full stack once built:
identical in shape to Track A (Gemini/Anthropic + FastAPI + React + Chroma
+ Docker), different **tools**, different **system prompt**, different
**output shape** (draft replies + escalations instead of patches).

**Read this side-by-side with Track A's README.** The file structure and
the build sequence are near-identical. What differs is the agent's domain.

**This is a starter, not a finished app.** `backend/agent.py` and
`backend/tools.py` are stubs with `TODO` comments — you write the async
agent loop and its tools yourself across Module 43, then wrap it in a
streaming chat UI in Module 44.

---

## What differs from Track A

| Component | Track A — Codebase Q&A | Track B — Helpdesk |
|---|---|---|
| Corpus | TodoMagic codebase docs | Streakly KB articles |
| Chroma collection (Module 45) | `track-a-codebase` | `track-b-helpdesk` |
| Default model | `gemini-3.1-flash-lite` (Anthropic alt: Sonnet 5) | Same Gemini default (Anthropic alt: Haiku 4.5 — classify/retrieve/paraphrase needs less) |
| Tool 1 (Module 43) | `read_file` | `read_ticket` |
| Tool 2 (Module 43) | `list_files` | `list_tickets` |
| Tool 3 (Module 43) | `edit_file` → `draft_patch` (Module 55) | `draft_reply` |
| Tool 4 (Module 45) | `search_docs` | `search_kb` |
| Tool 5 (Module 55) | — | `escalate_to_human` *(new — Track B's action-gate exercise)* |
| Output | `patches/*.md` | `draft-replies/*.md` (+ `escalations/*.md` from Module 55) |
| UI palette | Orange accent | Blue accent; red for escalations |
| System prompt | "Codebase assistant" | "Helpdesk agent with escalation rules" |

Everything else — the streaming loop shape, the SSE events, the React
hook, the Docker multi-stage build, the test scaffolding — carries over
unchanged. The Day-3 lesson lands here: once you have the backend shape
right, swapping the domain is mostly system prompt + tools.

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env   # add your Gemini key (default) or Anthropic key

./scripts/seed-workspace.sh   # copies KB articles + sample tickets into workspace/

# Build the Chroma index search_kb (Module 45) reads from. One-time — do it
# now so it's ready when you get there. The corpus lives in a sibling
# project with its own venv; see ../chroma-corpora/README.md if you
# haven't set that up yet.
(cd ../chroma-corpora/track-b-helpdesk && python build.py)

cd ui && npm install && cd ..
./verify.sh
```

`./verify.sh` is green on a fresh clone — Module 43/44/45 tests are designed
to *skip* (not fail) until you've implemented the step they check. Run
`pytest -m m11` / `pytest -m m12` / `pytest -m m13` to check your own progress.

---

## Working the exercise

```bash
python run_agent.py "Summarise the open tickets. Group by theme."
python run_agent.py --stream "Summarise the open tickets. Group by theme."   # after Module 44
```

Once Module 44 is done:

```bash
# Terminal 1 — backend
track-b-server
# Terminal 2 — Vite on port 5174 (so both tracks can run side-by-side)
cd ui && npm run dev
```

curl:

```bash
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Summarise the open tickets."}'
```

Docker: `docker compose up --build`.

---

## Catching up

Same mechanism as Track A:

```bash
./scripts/checkpoint.sh m11-end   # overlays the Module 43 end state
./scripts/checkpoint.sh m12-end   # overlays the Module 44 end state
./scripts/checkpoint.sh m13-end   # overlays the Module 45 end state
```

This **overwrites** the files the checkpoint provides — commit or stash
first if you want to keep your own attempt. `reference/` is the same
content as a full browsable tree; see `reference/REFERENCE.md`. It stops
at Module 44 on purpose — Modules 45+ (like `m13-end` above) are only
available as checkpoints, not as an extended `reference/` tree.

---

## The tools, by the time you're through Module 55

| Tool | Purpose | Arrives |
|---|---|---|
| `list_tickets()` | List all tickets with status + theme | Module 43 |
| `read_ticket(ticket_id)` | Read a ticket's full contents | Module 43 |
| `draft_reply(ticket_id, body)` | Draft a reply for a human to review and send. Never sends. | Module 43 |
| `search_kb(query)` | Find relevant KB passages | Module 45 |
| `escalate_to_human(category, summary, priority)` | File an escalation for a human to pick up, behind a confirm gate | Module 55 |

### Escalation categories (Module 55)

One of: `billing` (refund > $20 or disputed charge), `account-recovery`
(user locked out, no 2FA backup), `security` (suspicious activity),
`legal` (child accounts, privacy-law requests, press), `bug-report`
(likely affecting multiple users), `product-complaint` (frustrated tone,
needs human empathy), `other`. Priorities: `low`, `normal`, `high`, `urgent`.

---

## Example prompts to try

From Module 43 on:

- *"Summarise the open tickets. Group by theme."*
- *"For the billing-related tickets, draft a reply citing policy."*
- *"Read ticket TKT-99999 and draft a reply."* → declines; ticket doesn't exist (Module 43, Step 9's error-recovery moment).

Once `search_kb` and `escalate_to_human` exist (Modules 13 and 18):

- *"How do I enable 2FA?"* → search_kb → draft_reply
- *"I was charged $49 and I don't have Plus."* → escalate_to_human (billing, high)
- *"Someone is using my account."* → escalate_to_human (security, urgent)
- *"What's my current streak?"* → cannot see user data; escalates or tells the user how to check themselves.

---

## The guardrails philosophy (Module 55)

The helpdesk agent's failure modes differ from the codebase Q&A agent's:

- **Inventing user data is the worst failure.** If the agent says "I can see you were charged on March 5th..." it's making things up. `FORBIDDEN_ACTIONS` explicitly includes `lookup_user`, `get_billing_history`, etc. — there's no tool that lets the agent invent these.
- **Taking action on the user's behalf is always wrong.** No cancelling, no password-reset. The agent drafts or escalates; a human acts.
- **Escalation is a first-class workflow, not a fallback.** The system prompt teaches the agent when to escalate. The UI renders escalation tool calls with a red border (`ToolCallBlock.tsx`).

See `backend/guardrails.py` for the full forbidden-actions list.

---

## File map

```
track-b-helpdesk-qa/
├── backend/
│   ├── settings.py       ← given: track-b paths, helpdesk model default
│   ├── guardrails.py     ← given: 13 forbidden actions vs Track A's 7
│   ├── tools.py          ← YOU WRITE (Module 43): Tool/ToolSet + handlers
│   ├── agent.py          ← YOU WRITE (Module 43 loop, Module 44 streaming)
│   └── server.py         ← YOU WRITE (Module 44): /api/chat SSE endpoint
├── run_agent.py           ← given: CLI entry point
├── ui/                    ← same components as Track A, different palette
├── sample_tickets/        ← seeded into workspace/tickets/
├── workspace/             ← KB articles + tickets (seeded — don't hand-edit)
├── draft-replies/         ← where draft_reply writes
├── escalations/           ← where escalate_to_human writes (Module 55+)
├── checkpoints/           ← catch-up snapshots (m11-end, m12-end, m13-end)
├── reference/             ← full browsable copy of the Module 44 end state
├── tests/
│   ├── test_scaffold.py   ← always green
│   ├── m11/                ← pytest -m m11
│   ├── m12/                ← pytest -m m12
│   └── m13/                ← pytest -m m13
├── scripts/{seed-workspace.sh,checkpoint.sh,test-reference.sh}
├── Dockerfile, docker-compose.yml, verify.sh, pyproject.toml, .env.example, .gitignore
```

---

## What this artefact is NOT

- **Not a real helpdesk backend.** A real product would integrate with a ticketing system (Zendesk, Linear, etc.) via API, not files. The file-based stubs here are pedagogical.
- **Not a replacement for human support.** The escalation paths assume a human on the other end.
- **Not tested against adversarial users.** Prompt-injection via a ticket message is a real concern in production; Module 55 covers the general pattern. The baseline here doesn't include injection-defence beyond sandbox paths and the forbidden-actions list.
