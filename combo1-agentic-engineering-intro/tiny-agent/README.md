# Tiny Agent — Combo 1, Module 1

A Python coding agent in under 200 lines. Built with Google Gemini, mirrors Thorsten Ball's [*"How to build an agent"*](https://ampcode.com/how-to-build-an-agent) — same three tools, same conceptual shape, Python instead of Go.

> *"It's an LLM, a loop, and enough tokens."*
> — Thorsten Ball

This repo is the basis for the **M1: Build a Tiny Agent** exercise. In the 1-day variant you work in `starter/` and make it run. In the half-day variant the facilitator live-codes against `reference/` and you follow along.

---

## Setup (do this BEFORE the workshop)

1. **Python 3.12 or later.** Check with `python3 --version`.
2. **A Gemini API key.** Free tier is fine for the workshop. Get one at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).
3. **Install dependencies:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate       # or .venv\Scripts\activate on Windows
   pip install -e .
   ```
4. **Add your key:**
   ```bash
   cp .env.example .env
   # Edit .env and paste your GOOGLE_API_KEY
   ```
5. **Verify:**
   ```bash
   ./verify.sh
   ```
   If all checks pass you're ready. If something fails, see `FACILITATOR.md` for common issues.

---

## What you build

An agent that can operate on a small codebase (`sample_repo/`) by calling three tools:

| Tool | Signature | What it does |
|---|---|---|
| `read_file` | `read_file(path) -> str` | Return the contents of a file |
| `list_files` | `list_files(path=".") -> list[str]` | List entries in a directory |
| `edit_file` | `edit_file(path, old_str, new_str) -> str` | Replace a string in a file (exactly once) |

The agent **loops**: ask Gemini, run any tools it wants to call, feed the results back, repeat until Gemini stops calling tools.

---

## The exercise (1-day variant — ~75 minutes)

**Step 1 — The loop (30 min).** Open `starter/agent.py`. Find the `run_agent` function with the TODO. Make it work. The loop shape is documented in the file.

**Step 2 — The tools (25 min).** Open `starter/tools.py`. Implement `read_file`, `list_files`, and `edit_file`. Each function has clear TODOs. Run the tests as you go:
```bash
pytest tests/
```
(The tests import the bundled `reference/` implementation by default, so they pass out of the box. To check *your* code, change the import block at the top of `tests/test_tools.py` to point at `starter.tools` instead of `reference.tools` — they'll go red until you've implemented all three, then green again.)

**Step 3 — Drive the agent (10 min).**
```bash
cd sample_repo
python -m starter.agent "List the files here and give me a summary"
```
Then work through `sample_repo/TODO.md` — starting with a simple exploration prompt, then the bug-fix in `math_utils.py`.

**Step 4 — Debrief (10 min).** Discuss with your pair:
- Where did your agent get stuck? Why?
- What would you *not* trust this agent to do, right now?
- What's the simplest possible thing a framework like LangChain adds on top of this? (Answer: surprisingly little of value.)

**Stretch (if you finish early).** Add a fourth tool — `run_tests() -> str` that shells out to `pytest` and returns the output. Watch the agent use it to validate its own edits.

---

## The exercise (half-day variant)

The facilitator live-codes the reference implementation over ~40 minutes. You follow along in a pre-populated repo (this one) but are not expected to finish. Focus on understanding the loop shape and asking questions — not on typing.

---

## Running the reference implementation

The complete `reference/` implementation ships in this repo — peek at it if you
get stuck, or run it to compare behaviour with your own `starter/` version:

```bash
cd sample_repo
python -m reference.agent "Look through math_utils.py for bugs. If you find one, fix it."
# swap `reference` for `starter` to drive your own implementation
```

---

## What lives where

```
tiny-agent/
├── README.md                 ← you are here
├── FACILITATOR.md            ← notes for the person running the workshop
├── pyproject.toml            ← dependencies
├── .env.example
├── verify.sh                 ← pre-flight check
├── sample_repo/              ← the codebase the agent operates on
│   ├── README.md
│   ├── hello.py
│   ├── math_utils.py         (has a deliberate bug)
│   └── TODO.md               (tasks you can ask the agent to do)
├── starter/                  ← YOU WORK HERE
│   ├── tools.py              (with TODOs)
│   └── agent.py              (with TODOs)
├── reference/                ← complete worked solution (peek if you get stuck)
│   ├── tools.py
│   └── agent.py
└── tests/
    └── test_tools.py         (contract tests for your tool implementations)
```

---

## Post-workshop

Take this repo home. Three directions to explore further:

1. **Port to Anthropic.** The conceptual shape is identical — Claude uses `stop_reason: "tool_use"` + `tool_use` content blocks instead of Gemini's `function_call` parts. See `platform.claude.com/docs/en/agents-and-tools/tool-use/overview`.

2. **Read the original.** Thorsten Ball's [ampcode walkthrough](https://ampcode.com/how-to-build-an-agent) (Go, ~400 lines) is the canonical reference. Now that you've built one, his "holy shit, that's all there is" reaction will land.

3. **Make it stream.** The current code waits for the full response each turn. Swap `generate_content` for `generate_content_stream` and pipe chunks to stdout. Workshop Combo 3 covers this in depth.
