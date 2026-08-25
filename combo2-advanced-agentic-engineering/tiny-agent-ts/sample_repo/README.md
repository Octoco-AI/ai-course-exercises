# Sample Repo

A deliberately small codebase the tiny agent can operate on. Contains a couple of files with intentional problems for the agent to discover and fix.

## Contents

- `hello.ts` — simple greeting helper.
- `mathUtils.ts` — small library with a few helpers. Has a bug.
- `TODO.md` — a list of tasks you can ask the agent to do.

## Running the agent against this

From `sample_repo/`, with `GOOGLE_API_KEY` set:

```bash
cd sample_repo
npx tsx ../src/cli.ts "List the files here and give me a summary of what this codebase does"
```

The agent's sandbox is whatever directory you start it in, so running from here
is what keeps it pointed at these files.

Or pick any task from `TODO.md` and paste it as the prompt.
