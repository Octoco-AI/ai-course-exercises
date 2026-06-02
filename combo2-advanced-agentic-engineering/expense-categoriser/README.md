# Expense Categoriser — Combo 2, Module 5

A small FastAPI service that categorises expenses using Google Gemini, with a **three-layer testing strategy** and a **CI pipeline that blocks merges on eval regressions**.

This is the reference repo for Combo 2 M5 (*CI/CD/CE in practice*). You use it to see the pipeline in action, then extend it with evals you wrote in M4.

> Your deployment pipeline is green. Your model is live. And somewhere in production, it's quietly failing.
> — Herman Lintvelt, *CI/CD/CE: The Third Pillar of AI Development*

---

## What's here

```
expense-categoriser/
├── src/expense_categoriser/
│   ├── core.py                  ← categoriser logic (pure + LLM client)
│   ├── api.py                   ← FastAPI app
│   └── models.py                ← Pydantic + canonical categories
├── tests/
│   ├── test_core.py             ← Unit tests (fast, no API key)
│   ├── test_api.py              ← FastAPI endpoint tests
│   └── evals/
│       ├── test_categorisation_quality.py ← DeepEval-style suite
│       └── eval_dataset.json    ← 22-case golden dataset
├── .github/workflows/
│   ├── tests.yml                ← Runs unit + API tests on every push
│   └── evals.yml                ← Runs eval suite on every PR
└── scripts/
    └── create-regression-branch.sh  ← Deliberate regression for the demo
```

---

## Setup (pre-workshop)

```bash
python3 -m venv .venv
source .venv/bin/activate          # or .venv\Scripts\activate on Windows
pip install -e '.[dev]'
cp .env.example .env
# Edit .env, paste your Gemini key (https://aistudio.google.com/apikey)
./verify.sh                         # sanity check, no API calls
./verify.sh --evals                 # full check including one eval run (~30s)
```

---

## Running locally

```bash
expense-api                         # starts FastAPI on :8000 with reload

# Or directly:
uvicorn expense_categoriser.api:app --reload
```

Try it:

```bash
curl -X POST http://localhost:8000/categorise \
     -H "Content-Type: application/json" \
     -d '{"description": "Whole Foods Market", "amount": 78.23}'
# => {"category": "Food & Dining", "confidence": 0.95, "used_fallback": false}
```

---

## The three testing layers

Straight out of Herman's *"Testing the Untestable"*:

### 1. Unit tests — deterministic parts

File: `tests/test_core.py`.

Tests the pure functions (`build_prompt`, `parse_response`, `apply_confidence_threshold`) and confirms they handle edge cases (malformed JSON, unknown categories, out-of-range confidence) without calling the LLM.

**Run**: `pytest -v -m "not evals"` (default).

### 2. Integration tests — behaviour via HTTP

File: `tests/test_api.py`.

Uses FastAPI's `TestClient` to exercise the HTTP layer. The LLM is mocked — we're testing wiring (status codes, response shapes, error handling), not AI quality.

**Run**: same as unit tests. These are the non-evals suite.

### 3. Evals — quality at scale

Files: `tests/evals/test_categorisation_quality.py`, `tests/evals/eval_dataset.json`.

Runs real Gemini against a 22-case golden dataset with **acceptable** and **unacceptable** categories per case (ranges, not single answers — AI has multiple valid responses, and the eval respects that).

Four gates:

1. **Accuracy ≥ 85%** — of cases, ≥ 85% must pick an acceptable category.
2. **Zero catastrophic failures** — no case may be categorised as an explicitly unacceptable category.
3. **p95 latency ≤ 3 s** — realistic for classification.
4. **High-confidence calibration** — when the model reports ≥ 0.8 confidence, ≥ 90% of those predictions should be acceptable.

**Run**: `pytest -v -m evals tests/evals/` (requires `GOOGLE_API_KEY`).

---

## CI: what happens on a PR

Two workflows, triggered on `pull_request`:

- **`tests.yml`** — unit + API tests. Fast. No secrets. Always runs.
- **`evals.yml`** — eval suite against real Gemini. Requires the `GOOGLE_API_KEY` secret to be configured in the repo (Settings → Secrets and variables → Actions).

A PR that fails either workflow cannot merge. That's the point.

---

## The regression demo (Combo 2 M5)

Run this on a fresh clone:

```bash
./scripts/create-regression-branch.sh
git push -u origin demo/regression-prompt
gh pr create --title "demo: regress the prompt" --body "Watch the eval workflow block this."
```

What happens:

1. The script creates a branch and tweaks the system prompt to bias toward "Other" for ambiguous cases.
2. Push the branch, open a PR.
3. `tests.yml` passes — unit tests don't care, the shape of the code is unchanged.
4. `evals.yml` **fails** — accuracy drops below 85%, because too many cases are now being categorised as "Other".
5. The PR is blocked from merging.
6. Revert the regression, push again, `evals.yml` goes green, PR merges.

This is the whole lesson of M5: evals are tests, in CI, that block on quality regressions, not just code-correctness regressions.

---

## Extending this in M5 (2-day workshop)

During the hands-on, you:

1. Fork or clone this repo.
2. Add one new eval case to `tests/evals/eval_dataset.json` — something your team's real users would send through (real transaction descriptions from your own product, with the right answer).
3. Run the eval suite locally to confirm it passes.
4. Commit. Push a PR. Watch the workflow run.
5. Deliberately break the prompt (or tighten the thresholds). Watch the PR get blocked.

At the end of the day you have a CI pipeline with real evals, enforced by the same merge gate as your unit tests.

---

## Where the numbers came from

The thresholds (85%, 0, 3 s, 0.9) aren't magical. They came from the **spec**. In a real project:

1. You write the spec using the four-extras pattern (Combo 2 M3).
2. The performance thresholds in the spec become the eval gates.
3. The graceful-degradation rules in the spec become fallback behaviours (see `apply_confidence_threshold`).
4. The failure-mode list becomes the catastrophic-failure set.

The spec and the evals are the same document, expressed twice — once in English, once in code.

---

## Further reading

- Herman's *"Testing the Untestable"* — the three-layer approach.
- Herman's *"CI/CD/CE: The Third Pillar"* — the pipeline design.
- DeepEval docs — https://www.deepeval.com/docs/getting-started
- `../../../_shared/eval-tooling-install.md` — install + friction notes for DeepEval / Inspect AI / Opik / Chroma on a workshop machine.
