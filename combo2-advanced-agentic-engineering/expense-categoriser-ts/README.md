# Expense Categoriser (TypeScript) — Combo 2, Modules 11 & 12

A small Fastify service that categorises expenses with Gemini, wrapped in **three layers of testing** — unit, API contract, and evals — with CI that blocks a merge when AI quality regresses.

> *"Test the deterministic parts traditionally. Test the AI boundary for contract conformance. Measure the AI itself via evals, at scale."*

This is the **TypeScript path**. Python is the workshop's main path and the exercise text uses Python code blocks; this repo is here so a TypeScript team can spend the modules on eval design rather than on `pytest`. The [C# path](../../csharp/expense-categoriser-csharp/) is the same service again.

> **The eval thresholds and the golden dataset are identical across all three languages**, on purpose. A cross-language debrief is only interesting if everyone is measuring the same thing.

---

## Setup (do this BEFORE the workshop)

1. **Node 22 or later.** Check with `node --version`.
2. **A Gemini API key.** Octoco AI provides one — it arrives in your pre-workshop email.
3. **Install:**
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
   ./verify.sh --evals    # optional: one real eval run (~30s, ~$0.01)
   ```

---

## The three layers

This is the whole point of the repo. Each layer answers a different question, costs a different amount, and fails for a different reason.

| Layer | What it tests | Needs a key? | Command |
|---|---|---|---|
| **1 — Unit** | Our deterministic code: prompt construction, response parsing, the confidence threshold | No | `npm test` |
| **2 — API contract** | The HTTP surface, with the LLM faked at the `LlmClient` seam | No | (same — they run together) |
| **3 — Evals** | The *model's* output quality, against a golden dataset | **Yes** | `npm run test:evals` |

Layers 1 and 2 are free, instant, and run on every push. Layer 3 costs money, takes ~30 seconds, and runs on every PR — where it can block a merge.

**The most common mistake teams make** is collapsing these into one. If your unit tests call a real model, they're slow, flaky and expensive. If your evals use a mock, they measure nothing.

### Running the service

```bash
npm run dev

curl -X POST http://localhost:5080/categorise \
     -H "Content-Type: application/json" \
     -d '{"description": "Whole Foods", "amount": 45.23}'
```

Three endpoints: `GET /health`, `GET /categories`, `POST /categorise`.

Note what `POST /categorise` returns when things go sideways:

- **Low model confidence → `200 OK`** with `"category": "Other"` and `"used_fallback": true`. Graceful degradation is a *success*; the client needs to know the model was unsure, not that the request failed.
- **Model returns unparseable output → `502 Bad Gateway`.** Not a 500. The service is healthy; the model misbehaved. That distinction is what lets a CE pipeline alert on model drift without drowning in ordinary server errors.

---

## M11 — Evals as tests

Write three evals against this service — one deterministic, one probabilistic, one catastrophic — and watch one fail deliberately.

Read `tests/evals/categorisationQuality.test.ts` first. It already has four gates, and they map to the three shapes the module teaches:

| Gate | Shape | Threshold |
|---|---|---|
| accuracy is above the threshold | probabilistic | ≥ 85% acceptable |
| has zero catastrophic failures | catastrophic | exactly 0 |
| p95 latency is below the ceiling | deterministic-ish | ≤ 3.0s |
| high-confidence predictions are reliable | calibration | ≥ 90% |

**Vitest equivalents of the pytest constructs the exercise sheet shows:**

| pytest | vitest |
|---|---|
| `@pytest.mark.evals` | a separate `evals` project in `vitest.config.ts` |
| `pytest -m evals` | `npm run test:evals` |
| `pytest -m "not evals"` | `npm test` |
| `@pytest.fixture(scope="module")` | `beforeAll` |
| `pytest.skip(...)` | `describe.skipIf(...)` / `ctx.skip(...)` |
| `@pytest.mark.parametrize` | `it.each([...])` |
| `@pytest.mark.flaky(reruns=1)` | `it(..., { retry: 1 })` |

Markers matter for the same reason in both languages: you do not want the eval suite running on every local save. **Evals are opt-in.** That is why the second vitest project exists and why `tests.yml` runs only the first.

---

## M12 — CI/CD/CE in practice

Fork this repo, add one of your M11 evals to the CI gate, push a regression, watch the PR block, then fix it.

Two workflows ship in `.github/workflows/`:

- **`tests.yml`** — typecheck + unit + API on every push and PR. No key. Fast.
- **`evals.yml`** — the eval suite on every PR, using the `GOOGLE_API_KEY` repo secret. **A failing eval blocks the merge.**

To see it happen, there's a script that plants a deliberate regression:

```bash
./scripts/create-regression-branch.sh
```

It branches off main and biases the system prompt toward "Other" for anything not perfectly obvious. Push it, open a PR, and watch `evals.yml` fail on `ACCURACY_THRESHOLD` — a quality regression stopping a merge exactly the way a failing unit test would.

You'll need to add `GOOGLE_API_KEY` under **Settings → Secrets and variables → Actions** in your fork first.

---

## What lives where

```
expense-categoriser-ts/
├── README.md                       ← you are here
├── package.json  tsconfig.json  vitest.config.ts
├── .env.example
├── verify.sh
├── .github/workflows/
│   ├── tests.yml                   (layers 1+2 — every push, no key)
│   └── evals.yml                   (layer 3 — every PR, blocks the merge)
├── scripts/
│   └── create-regression-branch.sh
├── src/
│   ├── models.ts                   (Zod contracts + canonical category list)
│   ├── core.ts                     (the four testable seams)
│   ├── geminiClient.ts             (LlmClient over @google/genai)
│   ├── app.ts                      (Fastify app factory)
│   └── server.ts                   (entrypoint)
└── tests/
    ├── core.test.ts                (layer 1 — 16 unit tests)
    ├── api.test.ts                 (layer 2 — 7 contract tests)
    ├── fakeLlmClient.ts            (the seam that makes 1+2 free)
    └── evals/
        ├── categorisationQuality.test.ts   (layer 3 — 4 gates + a summary)
        └── eval_dataset.json               (22 golden cases)
```

`core.ts` is deliberately pulled apart into `buildPrompt`, `parseResponse`, `applyConfidenceThreshold` and `categorise`. That decomposition is not decoration — it is what makes layer 1 possible at all. Most AI features are hard to test because nobody separated the deterministic parts from the model call.

---

## Notes for the TypeScript path

**Zod does double duty.** It validates the incoming HTTP body *and* the model's JSON reply. That second use is the interesting one: the model is an untrusted input source exactly like a browser is, and `parseResponse` treats it that way. If your Angular app already validates API responses at the boundary, this will feel familiar — it is the same instinct pointed at a new source.

**`buildApp(client)` is a factory, not a module-level singleton.** That is what lets `api.test.ts` inject a `FakeLlmClient` and boot the real routes in-process. `app.inject()` dispatches straight into the router without opening a socket, so layer 2 runs in milliseconds.

**The eval suite deliberately does not use that seam** — it constructs a real `GeminiClient`. That's the line between layer 2 and layer 3.

**Two settings in `geminiClient.ts` matter and are easy to miss:** `responseMimeType: "application/json"` (ask for JSON rather than hoping) and `temperature: 0.1` (this is classification, not creativity).

---

## Post-workshop

1. **Grow the dataset.** 22 cases is a fast CI loop, not a real eval set. Add the transactions your own users actually submit, especially the ambiguous ones.
2. **Add a nightly run.** PR evals should be fast; nightly evals can afford 200+ cases and tighter thresholds.
3. **Track drift over time.** Log accuracy per run and alert on the trend, not just the threshold. A model that degrades from 96% to 87% is still passing — and still worth knowing about.
