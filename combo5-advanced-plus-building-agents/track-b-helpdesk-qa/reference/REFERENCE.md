# Reference implementation — Module 12 end state

Facilitator/attendee reference only. Not imported by the test suite, not
wired into the live `backend`/`ui` package — it's a browsable copy of what
a diligent pair produces by the end of Module 12: the async agent loop
(Module 11) turned into a streaming SSE backend with a working chat UI
(Module 12).

Three tools only — `list_tickets`, `read_ticket`, `draft_reply` — matching
the M11/M12 exercise scope. Modules 13-19 keep extending this same file set
(Module 13 adds a `search_kb` tool over the Chroma KB corpus; Module 18
adds `escalate_to_human` plus an action-gate pattern; and so on) — their
own exercise docs specify those changes in full, so this reference doesn't
pre-build them.

## How to actually run this code

It's not a drop-in package (avoids a second FastAPI singleton fighting the
live one during import). To try it end-to-end, use
`./scripts/checkpoint.sh m12-end` from the repo root instead — that
overlays the equivalent files onto the live `backend/`/`ui/` tree, which
you can then run normally (`uvicorn backend.server:app`, `cd ui && npm run
dev`, or `python run_agent.py --stream "..."`).

## What's here

```
backend/
  settings.py     unchanged from the starter (given from Module 11 on)
  guardrails.py   unchanged from the starter (given from Module 11 on)
  tools.py        Module 11 Phase 2 end state (ToolError, tightened description)
  agent.py        Module 12 end state (run_agent_streaming)
  streaming.py    Module 12, Step A.2
  server.py       Module 12, Step A.3 (/api/chat wired)
ui/src/
  hooks/useStreamingChat.ts        Module 12, Steps B.2-B.3
  components/ToolCallBlock.tsx     Module 12, Step B.5
  App.tsx, ChatPanel.tsx, Message.tsx, InputBar.tsx, main.tsx, styles.css
                                    given scaffold, unchanged throughout
```
