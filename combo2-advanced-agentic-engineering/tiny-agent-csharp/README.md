# Tiny Agent (C#) — Module 8

A C# coding agent in under 200 lines. Built on Google Gemini with nothing but `HttpClient` and `System.Text.Json` — no SDK, no framework. Mirrors Thorsten Ball's ["How to build an agent"](https://ampcode.com/how-to-build-an-agent) — same three tools, same conceptual shape, C# instead of Go.

> *"It's an LLM, a loop, and enough tokens."*
> — Thorsten Ball

This is the **C# path** through the M8 exercise. Python is the workshop's main path and the exercise text uses Python code blocks; this repo is here so a .NET team can spend the hour on agent loops rather than on `venv`. The [TypeScript path](../../typescript/tiny-agent-ts/) is the same exercise again.

> **You do not need to know Python to do this exercise.** Everything the exercise asks for exists here in C#, and the concepts are identical. Where the exercise sheet shows Python, the equivalent C# is named in the step comments.

---

## Setup (do this BEFORE the workshop)

1. **.NET SDK 10 or later.** Check with `dotnet --version`. Install from [dotnet.microsoft.com/download](https://dotnet.microsoft.com/download).
2. **A Gemini API key.** Octoco AI provides one for the workshop — it arrives in your pre-workshop email. Outside the workshop, the free tier at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) is fine.
3. **Restore and build:**
   ```bash
   dotnet build
   ```
4. **Add your key:**
   ```bash
   cp .env.example .env
   # Edit .env and paste your GOOGLE_API_KEY
   ```
5. **Verify:**
   ```bash
   ./verify.sh          # macOS / Linux / WSL
   pwsh ./verify.ps1    # Windows, PowerShell 7+
   ```
   If all checks pass you're ready. Note that "your tool tests fail as expected" is a **pass** — you write those tools during the exercise.

> **Windows attendees:** unlike the Python path, this one needs no WSL. Run it natively in PowerShell 7+. (Module 10's SpecKit exercise still wants WSL2 — see the prerequisites doc.)

---

## What you build

An agent that can operate on a small codebase (`sample_repo/`) by calling three tools:

| Tool | Signature | What it does |
|---|---|---|
| `read_file` | `ReadFile(path)` | Return the contents of a file |
| `list_files` | `ListFiles(path = ".")` | List entries in a directory |
| `edit_file` | `EditFile(path, oldStr, newStr)` | Replace a string in a file (exactly once) |

The agent **loops**: ask Gemini, run any tools it wants to call, feed the results back, repeat until Gemini stops calling tools.

---

## The exercise (~75 minutes)

**Step 1 — The loop (30 min).** Open `src/TinyAgent.Starter/Agent.cs`. Find `RunAsync` with the TODO. Make it work. The loop shape and the exact API calls you need are documented in the XML comment above it. The 7 tests in `AgentLoopTests.cs` check your loop against a canned model — offline, no API key, no spend — so you can run them as you go:
```bash
dotnet test --filter AgentLoop
```

**Step 2 — The tools (25 min).** Open `src/TinyAgent.Starter/Tools.cs`. Implement `ReadFile`, `ListFiles`, and `EditFile`. Each has clear TODOs. Run the tests as you go:
```bash
dotnet test
```
The tests point at **your** code by default — both the loop and the tools — and will be red until you've written all four pieces. To see them green against the worked solution:
```bash
TINY_AGENT_IMPL=reference dotnet test
```

**Step 3 — Drive the agent (10 min).**
```bash
cd sample_repo
dotnet run --project ../src/TinyAgent.Starter -- "List the files here and give me a summary"
```
Then work through `sample_repo/TODO.md` — start with a simple exploration prompt, then the bug-fix in `MathUtils.cs`.

**Step 4 — Debrief (10 min).** Discuss with your pair:
- Where did your agent get stuck? Why?
- What would you *not* trust this agent to do, right now?
- What's the simplest possible thing a framework like Semantic Kernel adds on top of this? (Answer: surprisingly little of value.)

**Stretch (if you finish early).** Add a fourth tool — `run_tests()` that shells out to `dotnet test` and returns the output. Watch the agent use it to validate its own edits. You'll need to add a schema for it in `ToolSchemas.cs` and a case in `Agent.Dispatch`.

---

## Two things that differ from the Python path

Worth knowing before you start, so neither surprises you mid-exercise.

**1. You write the tool schemas; Python generates them.** The Gemini Python SDK reads type hints and docstrings at runtime and builds the JSON schema for you. C# has no runtime-readable docstrings, so `src/TinyAgent.Shared/ToolSchemas.cs` spells the schema out — and it is given to you, not homework.

This is a fair trade. What the model actually receives is *exactly that JSON* in both languages; Python just hides it. When a model calls a tool wrongly, this file is what you need to read — and Python attendees have to go digging for it.

**2. The loop is `async`, and that's unavoidable.** The Python version is deliberately synchronous — its notes say "not a chance to teach asyncio". Every .NET HTTP call is a `Task`, so `await` shows up whether we want it or not. It is plumbing, not the lesson. Read past it and look at the loop.

There's a third difference that works in your favour: the Python version has to pass `automatic_function_calling=AutomaticFunctionCallingConfig(disable=True)` to stop the SDK running the tools *for* you and handing back only the final answer. At the REST layer there is nothing to disable — **the loop is always yours**. Same lesson, arrived at from the other side.

---

## Running the reference implementation

The complete `TinyAgent.Reference` project ships in this repo — peek at it if you get stuck, or run it to compare behaviour with your own:

```bash
cd sample_repo
dotnet run --project ../src/TinyAgent.Reference -- "Look through MathUtils.cs for bugs. If you find one, fix it."
```

Swap `TinyAgent.Reference` for `TinyAgent.Starter` to drive your own implementation.

---

## What lives where

```
tiny-agent-csharp/
├── README.md                       ← you are here
├── TinyAgent.sln
├── Directory.Build.props           ← shared build settings (net10.0, nullable)
├── .env.example
├── verify.sh / verify.ps1          ← pre-flight check
├── sample_repo/                    ← the codebase the agent operates on
│   ├── Hello.cs
│   ├── MathUtils.cs                (has a deliberate bug)
│   ├── README.md
│   └── TODO.md                     (tasks you can ask the agent to do)
├── src/
│   ├── TinyAgent.Shared/           ← GIVEN — read it, don't rewrite it
│   │   ├── GeminiClient.cs         (~50 lines of HttpClient — the whole "SDK")
│   │   ├── GeminiWire.cs           (the REST wire format, as records)
│   │   ├── ToolSchemas.cs          (what the model sees for each tool)
│   │   ├── PathSandbox.cs          (path-safety helper)
│   │   ├── ITools.cs, AgentEvent.cs, DotEnv.cs, Cli.cs
│   │   └── TinyAgent.Shared.csproj
│   ├── TinyAgent.Starter/          ← YOU WORK HERE
│   │   ├── Agent.cs                (RunAsync has the TODO)
│   │   └── Tools.cs                (three TODOs)
│   └── TinyAgent.Reference/        ← complete worked solution (peek if stuck)
└── tests/TinyAgent.Tests/
    ├── ToolsTests.cs               (15 contract tests for your tools)
    ├── AgentLoopTests.cs           (7 loop tests, offline — no API key needed)
    └── FakeGemini.cs               (canned model for the loop tests)
```

`AgentLoopTests` are worth a look even before you start. They test your loop against a scripted model with no network and no spend, and they assert on the three things that most often go wrong: appending the model's own turn, sending tool results under the right role, and terminating. The tools they call are always the reference ones, so they stay red-or-green on the strength of step 1 alone.

---

## Post-workshop

Take this repo home. Three directions to explore further:

1. **Swap in `Microsoft.Extensions.AI`.** The raw `HttpClient` here is for learning; `Microsoft.Extensions.AI` is the idiomatic .NET abstraction, and `AIFunctionFactory.Create` will generate tool schemas from `[Description]` attributes much like the Python SDK does from docstrings. Now that you've seen the wire format, that abstraction will read as a convenience rather than magic.

2. **Read the original.** Thorsten Ball's [ampcode walkthrough](https://ampcode.com/how-to-build-an-agent) (Go, ~400 lines) is the canonical reference. Now that you've built one, his "holy shit, that's all there is" reaction will land.

3. **Make it stream.** The current code waits for the full response each turn. Swap `:generateContent` for `:streamGenerateContent` and pipe chunks to stdout. Workshop Combo 3 covers this in depth.
