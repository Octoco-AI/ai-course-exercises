# Reference implementation — Module 3 end state

Facilitator/attendee reference only. Not imported by the test suite, not
wired into the live `backend`/`ui` package — it's a browsable copy of what
a diligent pair produces by the end of Module 3: the blocking agent loop
(Module 1, refined in Module 2) turned into a streaming SSE backend with a
working chat UI (Module 3).

Three tools only — `read_file`, `list_files`, `edit_file` — matching the
M1/M2/M3 exercise scope. Modules 4-12 keep extending this same file set
(Module 4 adds a `search_docs` tool over the Chroma corpus; Module 9
converts `edit_file` into a non-mutating `draft_patch`; and so on) — their
own exercise docs specify those changes in full, so this reference doesn't
pre-build them.

## How to actually run this code

It's not a drop-in package. To try it end-to-end, use
`./scripts/checkpoint.sh m3-end` from the repo root instead — that
overlays the equivalent files onto the live `backend/`/`ui/` tree, which
you can then run normally (`uvicorn backend.server:app`, `cd ui && npm run
dev`, or `python run_agent.py --stream "..."`).

## What's here

```
backend/
  settings.py     unchanged from the starter (given from Module 1 on)
  guardrails.py   unchanged from the starter (given from Module 1 on)
  tools.py        Module 2 end state (ToolError, tightened description)
  agent.py        Module 3 end state (run_agent_streaming)
  streaming.py    Module 3, Part A
  server.py       Module 3, Part A (/api/chat wired)
ui/src/
  hooks/useStreamingChat.ts        Module 3, Part B
  components/ToolCallBlock.tsx     Module 3, Part B
  App.tsx, ChatPanel.tsx, Message.tsx, InputBar.tsx, main.tsx, styles.css
                                    given scaffold, unchanged throughout
```
