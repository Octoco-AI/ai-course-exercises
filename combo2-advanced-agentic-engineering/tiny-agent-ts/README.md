# Tiny Agent (TypeScript) — Module 8

A TypeScript coding agent in under 200 lines. Built with Google Gemini via the official `@google/genai` SDK, mirroring Thorsten Ball's ["How to build an agent"](https://ampcode.com/how-to-build-an-agent) — same three tools, same conceptual shape, TypeScript instead of Go.

> *"It's an LLM, a loop, and enough tokens."*
> — Thorsten Ball

This is the **TypeScript path** through the M8 exercise. Python is the workshop's main path and the exercise text uses Python code blocks; this repo is here so a TypeScript team can spend the hour on agent loops rather than on `venv`. The [C# path](../../csharp/tiny-agent-csharp/) is the same exercise again.

> **You do not need to know Python to do this exercise.** Everything the exercise asks for exists here in TypeScript, and the concepts are identical. Where the exercise sheet shows Python, the equivalent TypeScript is named in the step comments.

---

## Setup (do this BEFORE the workshop)

1. **Node 22 or later.** Check with `node --version`.
2. **A Gemini API key.** Octoco AI provides one for the workshop — it arrives in your pre-workshop email. Outside the workshop, the free tier at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) is fine.
3. **Install dependencies:**
   ```bash
   npm install
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
   If all checks pass you're ready. Note that "your tool tests fail as expected" is a **pass** — you write those tools during the exercise.

---

## What you build

An agent that can operate on a small codebase (`sample_repo/`) by calling three tools:

| Tool | Signature | What it does |
|---|---|---|
| `read_file` | `readFile(path)` | Return the contents of a file |
| `list_files` | `listFiles(path = ".")` | List entries in a directory |
| `edit_file` | `editFile(path, oldStr, newStr)` | Replace a string in a file (exactly once) |

The agent **loops**: ask Gemini, run any tools it wants to call, feed the results back, repeat until Gemini stops calling tools.

---

## The exercise (~75 minutes)

**Step 1 — The loop (30 min).** Open `src/starter/agent.ts`. Find `runAgent` with the TODO. Make it work. The loop shape and the exact SDK calls you need are in the doc comment above it. The 8 tests in `tests/agentLoop.test.ts` check your loop against a stubbed model — offline, no API key, no spend — so you can run them as you go:
```bash
npm test
```

**Step 2 — The tools (25 min).** Open `src/starter/tools.ts`. Implement `readFile`, `listFiles`, and `editFile`. Each has clear TODOs. Run the tests as you go:
```bash
npm test
```
The tests point at **your** code by default — both the loop and the tools — and will be red until you've written all four pieces. To see them green against the worked solution:
```bash
npm run test:reference
```

**Step 3 — Drive the agent (10 min).**
```bash
cd sample_repo
npx tsx ../src/cli.ts "List the files here and give me a summary"
```
Then work through `sample_repo/TODO.md` — start with a simple exploration prompt, then the bug-fix in `mathUtils.ts`.

**Step 4 — Debrief (10 min).** Discuss with your pair:
- Where did your agent get stuck? Why?
- What would you *not* trust this agent to do, right now?
- What's the simplest possible thing a framework like LangChain adds on top of this? (Answer: surprisingly little of value.)

**Stretch (if you finish early).** Add a fourth tool — `run_tests()` that shells out to `npm test` and returns the output. Watch the agent use it to validate its own edits. You'll need to add a declaration in `src/shared/toolSchemas.ts` and a case in `src/shared/dispatch.ts`.

---

## Two things that differ from the Python path

Worth knowing before you start, so neither surprises you mid-exercise.

**1. You write the tool schemas; Python generates them.** The Gemini Python SDK reads type hints and docstrings at runtime and builds the JSON schema for you. TypeScript erases its types at compile time, so there is nothing to introspect and `src/shared/toolSchemas.ts` spells the schema out — and it is given to you, not homework.

This is a fair trade. What the model actually receives is *exactly that object* in both languages; Python just hides it. When a model calls a tool wrongly, this file is what you need to read — and Python attendees have to go digging for it.

**2. The loop is `async`, and that's unavoidable.** The Python version is deliberately synchronous — its notes say "not a chance to teach asyncio". Every network call in JavaScript is a Promise, so `await` shows up whether we want it or not. It is plumbing, not the lesson. Read past it and look at the loop.

Everything else is close to one-for-one: `@google/genai` has the same `generateContent` call, the same `functionCall` parts, and the same `automaticFunctionCalling: { disable: true }` toggle that the Python SDK has. If you pair with a Python attendee at the debrief, you'll find you wrote the same program.

---

## Running the reference implementation

The complete `src/reference/` implementation ships in this repo — peek at it if you get stuck, or run it to compare behaviour with your own:

```bash
cd sample_repo
TINY_AGENT_IMPL=reference npx tsx ../src/cli.ts "Look through mathUtils.ts for bugs. If you find one, fix it."
```

Drop `TINY_AGENT_IMPL=reference` to drive your own implementation.

---

## What lives where

```
tiny-agent-ts/
├── README.md                       ← you are here
├── package.json                    ← dependencies and scripts
├── tsconfig.json  vitest.config.ts
├── .env.example
├── verify.sh                       ← pre-flight check
├── sample_repo/                    ← the codebase the agent operates on
│   ├── hello.ts
│   ├── mathUtils.ts                (has a deliberate bug)
│   ├── README.md
│   └── TODO.md                     (tasks you can ask the agent to do)
├── src/
│   ├── shared/                     ← GIVEN — read it, don't rewrite it
│   │   ├── toolSchemas.ts          (what the model sees for each tool)
│   │   ├── dispatch.ts             (routes a call to a tool)
│   │   ├── sandbox.ts              (path-safety helper)
│   │   └── types.ts                (the Tools interface, agent events)
│   ├── starter/                    ← YOU WORK HERE
│   │   ├── agent.ts                (runAgent has the TODO)
│   │   └── tools.ts                (three TODOs)
│   ├── reference/                  ← complete worked solution (peek if stuck)
│   └── cli.ts                      ← console entrypoint (given)
└── tests/
    ├── tools.test.ts               (15 contract tests for your tools)
    ├── agentLoop.test.ts           (8 loop tests, offline — no API key needed)
    └── impl.ts                     (the starter/reference switch)
```

`agentLoop.test.ts` is worth a look even before you start. It tests your loop against a stubbed model with no network and no spend, and asserts on the things that most often go wrong: appending the model's own turn, sending tool results under the right role, disabling automatic function calling, and terminating. The tools it calls are always the reference ones, so it stays red-or-green on the strength of step 1 alone.

---

## Post-workshop

Take this repo home. Three directions to explore further:

1. **Port to Anthropic.** The conceptual shape is identical — Claude uses `stop_reason: "tool_use"` and `tool_use` content blocks instead of Gemini's `functionCall` parts. See `platform.claude.com/docs/en/agents-and-tools/tool-use/overview`.

2. **Read the original.** Thorsten Ball's [ampcode walkthrough](https://ampcode.com/how-to-build-an-agent) (Go, ~400 lines) is the canonical reference. Now that you've built one, his "holy shit, that's all there is" reaction will land.

3. **Make it stream.** The current code waits for the full response each turn. Swap `generateContent` for `generateContentStream` and pipe chunks to stdout. Workshop Combo 3 covers this in depth.
