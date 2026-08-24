# Reference implementation — Module 33 end state

Facilitator/attendee reference only. Not imported by the test suite, not
wired into the live `backend`/`ui` package — it's a browsable copy of what
a diligent pair produces by the end of Module 33: the blocking agent loop
(Module 31, refined in Module 32) turned into a streaming SSE backend with a
working chat UI (Module 33).

Three tools only — `list_tickets`, `read_ticket`, `draft_reply` — matching
the M31/M32/M33 exercise scope. Modules 4-12 keep extending this same file set
(Module 34 adds a `search_kb` tool over the Chroma KB corpus; Module 39 adds
`escalate_to_human` plus an action-gate pattern; and so on) — their own
exercise docs specify those changes in full, so this reference doesn't
pre-build them.

## How to actually run this code

Use `./scripts/checkpoint.sh m3-end` from the repo root instead — that
overlays the equivalent files onto the live `backend/`/`ui/` tree, which
you can then run normally (`uvicorn backend.server:app`, `cd ui && npm run
dev`, or `python run_agent.py --stream "..."`).

## What's here

```
backend/
  settings.py     unchanged from the starter (given from Module 31 on)
  guardrails.py   unchanged from the starter (given from Module 31 on)
  tools.py        Module 32 end state (ToolError, tightened description)
  agent.py        Module 33 end state (run_agent_streaming)
  streaming.py    Module 33, Part A
  server.py       Module 33, Part A (/api/chat wired)
ui/src/
  hooks/useStreamingChat.ts        Module 33, Part B
  components/ToolCallBlock.tsx     Module 33, Part B
  App.tsx, ChatPanel.tsx, Message.tsx, InputBar.tsx, main.tsx, styles.css
                                    given scaffold, unchanged throughout
```
