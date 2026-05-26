# Sample Repo

A deliberately small codebase the tiny agent can operate on. Contains a couple of files with intentional problems for the agent to discover and fix.

## Contents

- `hello.py` — simple greeting script.
- `math_utils.py` — small library with a few helpers. Has a bug.
- `TODO.md` — a list of tasks you can ask the agent to do.

## Running the agent against this

From the tiny-agent root, with your venv active and `GOOGLE_API_KEY` set:

```bash
cd sample_repo
python -m reference.agent "List the files here and give me a summary of what this codebase does"
```

Or pick any task from `TODO.md` and paste it as the prompt.
