<!--
  THIS IS THE ONLY FILE YOU NEED TO EDIT.

  Replace everything below with your own task, then run the three scripts
  (see README.md). All three scripts read this file — keep it the same task
  for the monolithic run and the plan/execute run so the comparison is fair.

  A good task is:
    - Moderately complex (1-2 hours by hand; not a one-line fix).
    - Real (from your roadmap or a recent PR).
    - Mechanical to execute once a plan exists.
    - Testable (a clear "done" — tests pass, endpoint responds, etc.).

  Include: context, acceptance criteria, relevant file paths, and any
  "never do this" constraints. The agent reads/edits files inside the
  WORKSPACE directory you set in .env (default: the expense-categoriser repo).

  The default task below is the M7 "fallback task" and runs against the
  default WORKSPACE out of the box.
-->

# Feature: Add `GET /categories/top?k=3` endpoint to the expense-categoriser

## Context
- FastAPI app at `src/expense_categoriser/api.py`.
- Existing endpoints include `POST /categorise` — read it as a pattern reference.
- Pydantic models live in `src/expense_categoriser/models.py`.

## Acceptance criteria
- `GET /categories/top?k=<N>` returns the N categories most frequently assigned
  across the last 100 categorisation calls.
- `k` defaults to 3 if not provided.
- Response shape: `{"top": [{"category": str, "count": int}, ...]}`.
- If fewer than 100 categorisations have occurred, return what's available.
- A test in `tests/test_api.py` verifies the endpoint with `k=3` and `k=10`.

## Never
- Store PII in the frequency counter.
- Block on the LLM — this endpoint should respond in <50ms.
