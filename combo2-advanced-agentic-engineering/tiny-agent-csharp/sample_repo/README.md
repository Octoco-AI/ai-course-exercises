# Sample Repo

A deliberately small codebase the tiny agent can operate on. Contains a couple of files with intentional problems for the agent to discover and fix.

## Contents

- `Hello.cs` — simple greeting helper.
- `MathUtils.cs` — small library with a few helpers. Has a bug.
- `TODO.md` — a list of tasks you can ask the agent to do.

## Running the agent against this

From `sample_repo/`, with `GOOGLE_API_KEY` set:

```bash
cd sample_repo
dotnet run --project ../src/TinyAgent.Reference -- "List the files here and give me a summary of what this codebase does"
```

Swap `TinyAgent.Reference` for `TinyAgent.Starter` to drive your own implementation.

Or pick any task from `TODO.md` and paste it as the prompt.
