# Project Constitution

*The rules every AI feature in this project must follow. Claude Code reads this at the start of every session via CLAUDE.md.*

---

## Architecture

Describe the stack and architectural choices Claude should respect.

- **Language / framework**: (e.g. Python 3.12 + FastAPI; TypeScript + React + Vite)
- **AI providers**: (e.g. Anthropic for production, Gemini for dev)
- **Data store**: (e.g. Postgres for persistent state, Redis for sessions)
- **Patterns**: (e.g. MVVM on the frontend, repository pattern on the backend)

---

## AI feature principles

Rules that apply to every AI-touching feature.

- **Confidence indicators**: every AI output shown to a user must be accompanied by a visible confidence score or uncertainty signal. No silent "I don't know."
- **Graceful degradation**: when the AI isn't confident or is unavailable, we must show a manual or non-AI alternative — never a blank page.
- **Audit logging**: every AI decision that affects a user's account, money, or medical data must be logged with model, prompt, response, and confidence.
- **Feedback mechanisms**: every AI feature must include a way for users to signal a good or bad output. Explicit (thumbs up/down) or implicit (click-through, time-on-page).
- **Human-in-the-loop for destructive actions**: any action that deletes data, sends a payment, or contacts an external party requires explicit human confirmation. No autonomous destructive operations.

---

## Never-do items

Hard rules the AI must not cross under any circumstances. One per line — explicit, testable.

- Never make medical claims without a licensed practitioner's review.
- Never commit changes that fail the eval baseline on the main branch.
- Never push directly to `main`; always open a PR.
- Never log full prompts or responses containing PII.
- Never call any tool with `tool_choice: any` forcing when extended thinking is on.

---

## Delegation norms

How we decide what to delegate to an AI agent, what to delegate-and-review, and what to keep ourselves.

- **Fully delegated**: boilerplate, language ports, repetitive refactors, first-draft documentation, test scaffolding.
- **Delegated-with-review**: new feature work, API changes, tests for new code, spec drafts.
- **Owned by a human**: architecture choices, security-sensitive code, ambiguous requirements, novel algorithms, anything touching compliance.

---

## Review expectations

What "I reviewed this AI-generated code" means here.

- Read every line. Don't just skim.
- Run the tests, don't just trust the CI green.
- Check for common AI mistakes: fabricated imports, wrong function signatures, silent try/except, over-broad type hints.
- If the change is non-trivial, ask the AI to explain its reasoning before merging.

---

## Evaluation norms

How we measure AI features.

- Every AI feature ships with a pre-deployment eval suite that runs in CI.
- Every AI feature has production monitoring for: accuracy, latency, fallback rate.
- Eval sets grow from production failures; we don't keep static eval sets.
- We use `deepeval` for CI evals and `opik` for production tracing.

---

## Stylistic preferences

Small things that keep the codebase coherent.

- Prefer explicit over clever. One-line comprehensions are fine; four-level nested ones are not.
- Docstrings for public APIs; one-line comments only for non-obvious code.
- No emojis in source code or commit messages.
- Imports: stdlib, third-party, first-party, each alphabetised, blank line between groups.
