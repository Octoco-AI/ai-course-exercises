# Tiny Agent (Java) — Module 8

A Java coding agent in under 200 lines. Built on Google Gemini with nothing but `java.net.http.HttpClient` and Jackson — no SDK, no framework. Mirrors Thorsten Ball's ["How to build an agent"](https://ampcode.com/how-to-build-an-agent) — same three tools, same conceptual shape, Java instead of Go.

> *"It's an LLM, a loop, and enough tokens."*
> — Thorsten Ball

This is the **Java path** through the M8 exercise. Python is the workshop's main path and the exercise text uses Python code blocks; this repo is here so a Java/Spring team can spend the hour on agent loops rather than on `venv`. The [C# path](../../csharp/tiny-agent-csharp/) and [TypeScript path](../../typescript/tiny-agent-ts/) are the same exercise again.

> **You do not need to know Python to do this exercise.** Everything the exercise asks for exists here in Java, and the concepts are identical. Where the exercise sheet shows Python, the equivalent Java is named in the step comments.

---

## Setup (do this BEFORE the workshop)

1. **JDK 21 or later.** Check with `java -version`. Install a distribution such as [Eclipse Temurin](https://adoptium.net/) or [Amazon Corretto](https://aws.amazon.com/corretto/).
2. **A Gemini API key.** Octoco AI provides one for the workshop — it arrives in your pre-workshop email. Outside the workshop, the free tier at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) is fine.
3. **Build and install the modules.** A Maven wrapper is committed, so you don't need Maven installed — only a JDK:
   ```bash
   ./mvnw install -DskipTests
   ```
   This installs `tiny-agent-shared` (and the other modules) so `exec:java` can resolve them later. Re-run it if you change anything in `shared/`.
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
| `read_file` | `readFile(path)` | Return the contents of a file |
| `list_files` | `listFiles(path = ".")` | List entries in a directory |
| `edit_file` | `editFile(path, oldStr, newStr)` | Replace a string in a file (exactly once) |

The agent **loops**: ask Gemini, run any tools it wants to call, feed the results back, repeat until Gemini stops calling tools.

---

## The exercise (~75 minutes)

**Step 1 — The loop (30 min).** Open `starter/src/main/java/ai/octoco/tinyagent/starter/Agent.java`. Find `runAsync` with the TODO. Make it work. The loop shape and the exact API calls you need are documented in the Javadoc above it. The 7 tests in `AgentLoopTests.java` check your loop against a canned model — offline, no API key, no spend — so you can run them as you go:
```bash
./mvnw -pl tests -am test -Dtest=AgentLoopTests -Dsurefire.failIfNoSpecifiedTests=false
```

**Step 2 — The tools (25 min).** Open `starter/src/main/java/ai/octoco/tinyagent/starter/StarterTools.java`. Implement `readFile`, `listFiles`, and `editFile`. Each has clear TODOs. Run the tests as you go:
```bash
./mvnw -pl tests -am test
```
The tests point at **your** code by default — both the loop and the tools — and will be red until you've written all four pieces. To see them green against the worked solution:
```bash
TINY_AGENT_IMPL=reference ./mvnw -pl tests -am test
```

**Step 3 — Drive the agent (10 min).**
```bash
cd sample_repo
../mvnw -f ../starter/pom.xml exec:java -Dexec.args="List the files here and give me a summary"
```
Then work through `sample_repo/TODO.md` — start with a simple exploration prompt, then the bug-fix in `MathUtils.java`.

**Step 4 — Debrief (10 min).** Discuss with your pair:
- Where did your agent get stuck? Why?
- What would you *not* trust this agent to do, right now?
- What's the simplest possible thing a framework like Spring AI or LangChain4j adds on top of this? (Answer: surprisingly little of value.)

**Stretch (if you finish early).** Add a fourth tool — `run_tests()` that shells out to `./mvnw test` and returns the output. Watch the agent use it to validate its own edits. You'll need to add a schema for it in `ToolSchemas.java` and a case in `Agent.dispatch`.

---

## Three things that differ from the Python path

Worth knowing before you start, so none of them surprise you mid-exercise.

**1. You write the tool schemas; Python generates them.** The Gemini Python SDK reads type hints and docstrings at runtime and builds the JSON schema for you. Java has no runtime-readable docstrings, so `shared/src/main/java/ai/octoco/tinyagent/shared/ToolSchemas.java` spells the schema out — and it is given to you, not homework.

This is a fair trade. What the model actually receives is *exactly that JSON* in both languages; Python just hides it. When a model calls a tool wrongly, this file is what you need to read — and Python attendees have to go digging for it.

**2. The network calls are `CompletableFuture`, and that's unavoidable.** The Python version is deliberately synchronous — its notes say "not a chance to teach asyncio". `java.net.http.HttpClient.sendAsync` returns a `CompletableFuture`, so each turn calls `.join()` on it — the Java equivalent of `await`. It is plumbing, not the lesson. Read past it and look at the loop.

There's a third difference that works in your favour: the Python version has to pass `automatic_function_calling=AutomaticFunctionCallingConfig(disable=True)` to stop the SDK running the tools *for* you and handing back only the final answer. At the REST layer there is nothing to disable — **the loop is always yours**. Same lesson, arrived at from the other side.

**3. `.env` values live in a map, not the environment.** The C# port can call the equivalent of `Environment.SetEnvironmentVariable` to inject `.env` values into the process. The JVM has no public API to mutate its own environment block once started, so `DotEnv` keeps `.env` values in a private map instead and checks the real environment first. You'll never notice this while doing the exercise — it only matters if you go looking at `DotEnv.java`.

---

## Running the reference implementation

The complete `reference` module ships in this repo — peek at it if you get stuck, or run it to compare behaviour with your own:

```bash
cd sample_repo
../mvnw -f ../reference/pom.xml exec:java -Dexec.args="Look through MathUtils.java for bugs. If you find one, fix it."
```

Swap `../reference/pom.xml` for `../starter/pom.xml` to drive your own implementation.

---

## What lives where

```
tiny-agent-java/
├── README.md                       ← you are here
├── pom.xml                         ← parent aggregator (Java 21, module list)
├── mvnw / mvnw.cmd, .mvn/          ← committed Maven wrapper — no local Maven needed
├── .env.example
├── verify.sh / verify.ps1          ← pre-flight check
├── sample_repo/                    ← the codebase the agent operates on
│   ├── Hello.java
│   ├── MathUtils.java              (has a deliberate bug)
│   ├── README.md
│   └── TODO.md                     (tasks you can ask the agent to do)
├── shared/                         ← GIVEN — read it, don't rewrite it
│   └── src/main/java/ai/octoco/tinyagent/shared/
│       ├── GeminiClient.java       (built on java.net.http.HttpClient — the whole "SDK")
│       ├── GeminiRequest.java, Content.java, Part.java, ...  (the REST wire format, as records)
│       ├── ToolSchemas.java        (what the model sees for each tool)
│       ├── PathSandbox.java        (path-safety helper)
│       ├── Tools.java, ToolListResult.java, AgentEvent.java, DotEnv.java, Cli.java
│       └── GeminiTransport.java    (the seam used by offline tests)
├── starter/                        ← YOU WORK HERE
│   └── src/main/java/ai/octoco/tinyagent/starter/
│       ├── Agent.java              (runAsync has the TODO)
│       └── StarterTools.java       (three TODOs)
├── reference/                      ← complete worked solution (peek if stuck)
└── tests/src/test/java/ai/octoco/tinyagent/tests/
    ├── ToolsTests.java             (15 contract tests for your tools)
    ├── AgentLoopTests.java         (7 loop tests, offline — no API key needed)
    └── FakeGeminiTransport.java    (canned model for the loop tests)
```

`shared/` has more, smaller files than the Python/C#/TypeScript equivalents. That's not padding: Java only allows one public top-level type per file, so the wire-format records that live together in one file in other ports (`Content`, `Part`, `FunctionCall`, ...) each get their own file here.

`AgentLoopTests` are worth a look even before you start. They test your loop against a scripted model with no network and no spend, and they assert on the three things that most often go wrong: appending the model's own turn, sending tool results under the right role, and terminating. The tools they call are always the reference ones, so they stay red-or-green on the strength of step 1 alone.

---

## Post-workshop

Take this repo home. Three directions to explore further:

1. **Look at Spring AI or LangChain4j.** The raw `HttpClient` here is for learning; frameworks like these generate tool schemas from annotated methods much like the Python SDK does from docstrings. Now that you've seen the wire format, that abstraction will read as a convenience rather than magic.

2. **Read the original.** Thorsten Ball's [ampcode walkthrough](https://ampcode.com/how-to-build-an-agent) (Go, ~400 lines) is the canonical reference. Now that you've built one, his "holy shit, that's all there is" reaction will land.

3. **Make it stream.** The current code waits for the full response each turn. Swap `:generateContent` for `:streamGenerateContent` and process chunks as they arrive. Workshop Combo 3 covers this in depth.
