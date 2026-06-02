# Track B — Helpdesk agent (Combo 3 running artefact)

A streaming agent that answers Streakly support questions using the KB, drafts replies for a human to send, and escalates when a user-specific issue needs a human. Full stack identical in shape to Track A (FastAPI + React + Chroma + Docker), different **tools**, different **system prompt**, different **output shape** (drafts + escalations instead of patches).

**Read this side-by-side with Track A's README.** The file structure is 80% identical. What differs is the agent's job.

---

## What changed from Track A

| Component | Track A — Codebase Q&A | Track B — Helpdesk |
|---|---|---|
| Corpus | TodoMagic codebase docs | Streakly KB articles |
| Chroma collection | `track-a-codebase` | `track-b-helpdesk` |
| Default model | Sonnet 4.6 (more reasoning for code) | Haiku 4.5 (classify + retrieve + paraphrase) |
| Tool 1 | `search_docs` | `search_kb` |
| Tool 2 | `read_file` | `read_article` |
| Tool 3 | `list_files` | — *(removed; agent uses search)* |
| Tool 4 | `draft_patch` | `create_draft_reply` |
| Tool 5 | — | `escalate_to_human` *(new)* |
| Output | `patches/*.patch` | `draft-replies/*.md` + `escalations/*.md` |
| UI palette | Orange accent | Blue accent; red for escalations |
| System prompt | "Codebase assistant" | "Helpdesk agent with escalation rules" |

Everything else — the streaming loop, the SSE events, the React hook, the Docker multi-stage build, the test scaffolding — carries over unchanged. The Combo 3 lesson lands here: once you have the backend shape right, swapping the domain is mostly system prompt + tools.

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env   # edit, add your Anthropic key

./scripts/seed-workspace.sh                           # copies KB articles into workspace/
(cd ../chroma-corpora/track-b-helpdesk && python build.py)  # builds the Chroma index

cd ui && npm install && npm run build && cd ..
./verify.sh
```

---

## Running

```bash
# Terminal 1 — backend
track-b-server

# Terminal 2 (optional, for UI hot-reload) — Vite on port 5174 so both tracks can run side-by-side
cd ui && npm run dev
```

Open http://localhost:5174 (dev) or http://localhost:8000 (built-in-serving).

curl:

```bash
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I enable two-factor authentication?"}'
```

Docker:

```bash
docker compose up --build
```

---

## The four tools

| Tool | Purpose |
|---|---|
| `search_kb(query)` | Find relevant KB passages. Usually the first call. |
| `read_article(path)` | Read a full KB article when search snippets aren't enough. |
| `create_draft_reply(subject, body, tags)` | Write a reply email to `draft-replies/` for a human to review and send. |
| `escalate_to_human(category, summary, priority)` | File an escalation ticket to `escalations/` for a human to pick up. |

### Escalation categories

One of:
- `billing` — refund > $20 or disputed charge
- `account-recovery` — user can't access email and has no 2FA backup codes
- `security` — suspicious activity report
- `legal` — child accounts, privacy-law requests, press, complaints
- `bug-report` — likely affecting multiple users
- `product-complaint` — frustrated tone, human empathy needed
- `other` — anything else that needs a human

Priorities: `low`, `normal`, `high`, `urgent`.

---

## Example prompts to try

Answerable by the KB (agent drafts reply):

- *"How do I enable 2FA?"* → search_kb → create_draft_reply
- *"Why did my streak reset after I flew to Tokyo?"* → search_kb → create_draft_reply
- *"My widget isn't updating."* → search_kb → read_article → create_draft_reply

Escalation cases (agent opens ticket):

- *"I was charged $49 and I don't have Plus."* → escalate_to_human (billing, high)
- *"Someone is using my account."* → escalate_to_human (security, urgent)
- *"My 10-year-old signed up. Delete the account."* → escalate_to_human (legal, normal)
- *"I can't sign in and my email got hacked."* → escalate_to_human (account-recovery, high)

Graceful decline (agent should not pretend):

- *"What's my current streak?"* → cannot see user data; must escalate or tell the user how to check themselves
- *"Cancel my subscription for me."* → cannot take action; tells user how to do it via Apple/Google

---

## The guardrails philosophy

The helpdesk agent's failure modes are different from the codebase Q&A agent's:

- **Inventing user data is the worst failure.** If the agent says "I can see you were charged on March 5th..." it's making things up. Grave for a support context. `FORBIDDEN_ACTIONS` explicitly includes `lookup_user`, `get_billing_history`, etc. — there's no tool that lets the agent invent these.
- **Taking action on the user's behalf is always wrong.** No cancelling, no password-reset, no account changes. The agent drafts, a human acts.
- **Escalation is not a fallback — it's a first-class workflow.** The system prompt teaches the agent when to escalate. The UI renders escalation tool calls with a red border (see `ToolCallBlock.tsx`).

See `backend/guardrails.py` for the full forbidden-actions list.

---

## How each Combo 3 module applies

See `../track-a-codebase-qa/README.md#how-each-combo-3-module-extends-this` — the same module-to-code mapping applies. Differences:

- **M7 (evals)** — the eval dataset for Track B should include categorisation cases: given a user question, did the agent search-and-draft, or did it escalate? That's a classification-style eval, different shape from Track A's trajectory evals. See `tests/test_agent.py` for the scaffold.
- **M9 (guardrails)** — Track B's forbidden-actions list is more varied (account-mutation, external-comms). Good teaching case: different domains have different "never do this" rules; the shape of the guardrails is the same.
- **M11 (deployment)** — same Dockerfile pattern, different volume mounts for `draft-replies/` and `escalations/`.

---

## File map

```
track-b-helpdesk-qa/
├── backend/
│   ├── settings.py            ← track-b paths, helpdesk model default (Haiku)
│   ├── guardrails.py          ← 13 forbidden actions vs Track A's 7
│   ├── tools.py               ← 4 helpdesk tools with schemas
│   ├── streaming.py           ← identical to Track A
│   ├── agent.py               ← same shape, different system prompt
│   └── server.py              ← identical to Track A
├── ui/                        ← same components, different palette + branding
├── workspace/                 ← KB articles, seeded from chroma-corpora
├── draft-replies/             ← where create_draft_reply writes
├── escalations/               ← where escalate_to_human writes
├── tests/                     ← 18 tests covering tools, guardrails, agent, api
├── scripts/seed-workspace.sh
├── Dockerfile + docker-compose.yml + verify.sh + pyproject.toml + .env.example + .gitignore
├── README.md
└── FACILITATOR.md
```

---

## What this artefact is NOT

- **Not a real helpdesk backend.** A real product would integrate with a ticketing system (Zendesk, Linear, etc.) via API, not files. The file-based stubs here are pedagogical.
- **Not a replacement for human support.** The escalation paths assume there's a human on the other end. The agent is a force multiplier, not an FTE replacement.
- **Not tested against adversarial users.** Prompt-injection via user message is a real concern in production; Combo 3 M9 exercise covers this. The baseline here doesn't include injection-defence beyond sandbox paths.
