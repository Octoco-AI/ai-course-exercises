# Project Constitution

*The rules every AI feature in this project must follow. Codex reads this at the start of every session via `AGENTS.md`.*

---

## Deriving this from a PRD

Unlike a cold-start constitution, this one starts from a document someone else wrote for a
different purpose. Three sources, three different confidence levels — label every line you
draft with which one it came from, so the human reviewing it can tell a PM decision from an
engineering assumption at a glance:

- `[derived from PRD §Out of scope]` or `[derived from PRD §Requirements]` — the PRD said
  this, directly or by clear implication. Highest confidence.
- `[from repo]` — Phase 0's bounded read of the codebase told you this. Verifiable, but not
  a decision anyone signed off on; it's just what's there today.
- `[assumed — confirm]` — you inferred it because most projects like this one do it this
  way, not because anything in the PRD or repo said so. Lowest confidence — flag it for the
  user to confirm or correct, don't let it sit unlabelled next to the other two.

**Delegation norms below cannot be derived from a PRD at all.** A product document has no
opinion on what an engineer should hand to an agent versus keep for themselves. Ask.

---

## Architecture

Describe the stack and architectural choices Codex should respect.

- **Language / framework**: (e.g. Python 3.12 + FastAPI; TypeScript + React + Vite) `[from repo]`
- **AI providers**: (e.g. Anthropic for production, Gemini for dev) `[from repo]`
- **Data store**: (e.g. Postgres for persistent state, Redis for sessions) `[from repo]`
- **Patterns**: (e.g. MVVM on the frontend, repository pattern on the backend) `[from repo]`

---

## AI feature principles

Rules that apply to every AI-touching feature. Draft these from the PRD's Goals and any
confidence or fallback language its requirements already contain — a requirement that says
"the system SHALL show a confirmation message" implies a principle about visible feedback
even though the PRD never states the principle directly.

- **Confidence indicators**: every AI output shown to a user must be accompanied by a visible confidence score or uncertainty signal. No silent "I don't know." `[assumed — confirm]`
- **Graceful degradation**: when the AI isn't confident or is unavailable, we must show a manual or non-AI alternative — never a blank page. `[derived from PRD §Requirements]`
- **Audit logging**: every AI decision that affects a user's account, money, or medical data must be logged with model, prompt, response, and confidence. `[assumed — confirm]`
- **Feedback mechanisms**: every AI feature must include a way for users to signal a good or bad output. Explicit (thumbs up/down) or implicit (click-through, time-on-page). `[assumed — confirm]`
- **Human-in-the-loop for destructive actions**: any action that deletes data, sends a payment, or contacts an external party requires explicit human confirmation. No autonomous destructive operations. `[derived from PRD §Out of scope]`

---

## Never-do items

Hard rules the AI must not cross under any circumstances. One per line — explicit, testable.
Draft these first from the PRD's `## Scope` → Out of scope bullets, which are often
never-do items in product language already.

- Never make medical claims without a licensed practitioner's review. `[assumed — confirm]`
- Never commit changes that fail the eval baseline on the main branch. `[assumed — confirm]`
- Never push directly to `main`; always open a PR. `[from repo]`
- Never log full prompts or responses containing PII. `[assumed — confirm]`
- <one per PRD "Out of scope" bullet that reads as a hard boundary, not just a deferred feature> `[derived from PRD §Out of scope]`

---

## Delegation norms

How we decide what to delegate to an AI agent, what to delegate-and-review, and what to keep
ourselves. **A PRD has no opinion on this — ask the user rather than guessing.**

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
