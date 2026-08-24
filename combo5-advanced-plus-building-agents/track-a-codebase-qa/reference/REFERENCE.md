# Reference implementation — Module 44 end state

Facilitator/attendee reference only. Not imported by the test suite, not
wired into the live `backend`/`ui` package — it's a browsable copy of what
a diligent pair produces by the end of Module 44: the async agent loop
(Module 43) turned into a streaming SSE backend with a working chat UI
(Module 44).

Three tools only — `read_file`, `list_files`, `edit_file` — matching the
M43/M44 exercise scope. Modules 13-19 keep extending this same file set
(Module 45 adds a `search_docs` tool over the Chroma corpus; Module 55
converts `edit_file` into a non-mutating `draft_patch`; and so on) — their
own exercise docs specify those changes in full, so this reference doesn't
pre-build them.

## How to actually run this code

It's not a drop-in package (avoids a second `chromadb`/FastAPI singleton
fighting the live one during import). To try it end-to-end, use
`./scripts/checkpoint.sh m12-end` from the repo root instead — that
overlays the equivalent files onto the live `backend/`/`ui/` tree, which
you can then run normally (`uvicorn backend.server:app`, `cd ui && npm run
dev`, or `python run_agent.py --stream "..."`).

## What's here

```
backend/
  settings.py     unchanged from the starter (given from Module 43 on)
  guardrails.py   unchanged from the starter (given from Module 43 on)
  tools.py        Module 43 Phase 2 end state (ToolError, tightened description)
  agent.py        Module 44 end state (run_agent_streaming)
  streaming.py    Module 44, Step A.2
  server.py       Module 44, Step A.3 (/api/chat wired)
ui/src/
  hooks/useStreamingChat.ts        Module 44, Steps B.2-B.3
  components/ToolCallBlock.tsx     Module 44, Step B.5
  App.tsx, ChatPanel.tsx, Message.tsx, InputBar.tsx, main.tsx, styles.css
                                    given scaffold, unchanged throughout
```
