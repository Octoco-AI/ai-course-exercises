# Expense Categoriser (Java) — Combo 2, Modules 11 & 12

A small Spring Boot service that categorises expenses with Gemini, wrapped in **three layers of testing** — unit, API contract, and evals — with CI that blocks a merge when AI quality regresses.

> *"Test the deterministic parts traditionally. Test the AI boundary for contract conformance. Measure the AI itself via evals, at scale."*

This is the **Java path**. Python is the workshop's main path and the exercise text uses Python code blocks; this repo is here so a Java/Spring team can spend the modules on eval design rather than on `pytest`. The [C# path](../../csharp/expense-categoriser-csharp/) and [TypeScript path](../../typescript/expense-categoriser-ts/) are the same service again.

> **The eval thresholds and the golden dataset are identical across all four languages**, on purpose. A cross-language debrief is only interesting if everyone is measuring the same thing.

---

## Setup (do this BEFORE the workshop)

1. **JDK 21 or later.** Check with `java -version`.
2. **A Gemini API key.** Octoco AI provides one — it arrives in your pre-workshop email.
3. **Build.** A Maven wrapper is committed, so you don't need Maven installed — only a JDK:
   ```bash
   ./mvnw compile
   ```
4. **Add your key:**
   ```bash
   cp .env.example .env
   # Edit .env and paste your GOOGLE_API_KEY
   ```
5. **Verify:**
   ```bash
   ./verify.sh                  # macOS / Linux / WSL
   pwsh ./verify.ps1            # Windows, PowerShell 7+

   ./verify.sh --evals          # optional: one real eval run (~30s, ~$0.01)
   ```

> **Windows attendees:** this path needs no WSL. Run it natively in PowerShell 7+.

---

## The three layers

This is the whole point of the repo. Each layer answers a different question, costs a different amount, and fails for a different reason.

| Layer | What it tests | Needs a key? | Command |
|---|---|---|---|
| **1 — Unit** | Our deterministic code: prompt construction, response parsing, the confidence threshold | No | `./mvnw test` |
| **2 — API contract** | The HTTP surface, with the LLM faked at the `LlmClient` seam | No | (same — they run together) |
| **3 — Evals** | The *model's* output quality, against a golden dataset | **Yes** | `./mvnw test -Dgroups=evals -DexcludedGroups=` |

Layers 1 and 2 are free, instant, and run on every push. Layer 3 costs money, takes ~30 seconds, and runs on every PR — where it can block a merge.

**The most common mistake teams make** is collapsing these into one. If your unit tests call a real model, they're slow, flaky and expensive. If your evals use a fake, they measure nothing.

### Running the service

```bash
./mvnw spring-boot:run

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

Read `src/test/java/ai/octoco/expensecategoriser/evals/CategorisationQualityTests.java` first. It already has four gates, and they map to the three shapes the module teaches:

| Gate | Shape | Threshold |
|---|---|---|
| `accuracyAboveThreshold` | probabilistic | ≥ 85% acceptable |
| `zeroCatastrophicFailures` | catastrophic | exactly 0 |
| `p95LatencyBelowCeiling` | deterministic-ish | ≤ 3.0s |
| `highConfidencePredictionsAreReliable` | calibration | ≥ 90% |

**JUnit 5 equivalents of the pytest constructs the exercise sheet shows:**

| pytest | JUnit 5 |
|---|---|
| `@pytest.mark.evals` | `@Tag("evals")` on the class |
| `pytest -m evals` | `./mvnw test -Dgroups=evals -DexcludedGroups=` |
| `pytest -m "not evals"` | `./mvnw test` (the pom.xml default excludes `evals`) |
| `@pytest.fixture(scope="module")` | `@TestInstance(PER_CLASS)` + `@BeforeAll` |
| `pytest.skip(...)` | `Assumptions.assumeTrue(...)` |
| `@pytest.mark.parametrize` | `@ParameterizedTest` + `@ValueSource`/`@CsvSource` |
| `@pytest.mark.flaky(reruns=1)` | retry in the test body, or a `@RepeatedTest`/rerun plugin |

Markers matter for the same reason in both languages: you do not want the eval suite running on every local save. **Evals are opt-in.** That is why the tag exists and why `tests.yml` doesn't set `-Dgroups=evals`.

---

## M12 — CI/CD/CE in practice

Fork this repo, add one of your M11 evals to the CI gate, push a regression, watch the PR block, then fix it.

Two workflows ship in `.github/workflows/`:

- **`tests.yml`** — unit + API on every push and PR. No key. Fast.
- **`evals.yml`** — the eval suite on every PR, using the `GOOGLE_API_KEY` repo secret. **A failing eval blocks the merge.**

To see it happen, there's a script that plants a deliberate regression:

```bash
./scripts/create-regression-branch.sh        # macOS / Linux / WSL
pwsh ./scripts/create-regression-branch.ps1  # Windows
```

It branches off main and biases the system prompt toward "Other" for anything not perfectly obvious. Push it, open a PR, and watch `evals.yml` fail on `accuracyAboveThreshold` — a quality regression stopping a merge exactly the way a failing unit test would.

You'll need to add `GOOGLE_API_KEY` under **Settings → Secrets and variables → Actions** in your fork first.

---

## What lives where

```
expense-categoriser-java/
├── README.md                       ← you are here
├── pom.xml
├── mvnw / mvnw.cmd, .mvn/          ← committed Maven wrapper — no local Maven needed
├── .env.example
├── verify.sh / verify.ps1
├── .github/workflows/
│   ├── tests.yml                   (layers 1+2 — every push, no key)
│   └── evals.yml                   (layer 3 — every PR, blocks the merge)
├── scripts/
│   └── create-regression-branch.sh / .ps1
└── src/
    ├── main/java/ai/octoco/expensecategoriser/
    │   ├── Models.java                          (contracts + canonical category list)
    │   ├── Core.java                             (the four testable seams)
    │   ├── LlmClient.java, GeminiClient.java      (the seam, and Gemini over HttpClient)
    │   ├── DotEnv.java
    │   └── ExpenseCategoriserApplication.java     (Spring Boot app + REST controller)
    └── test/java/ai/octoco/expensecategoriser/
        ├── CoreTests.java                        (layer 1 — 16 unit tests)
        ├── ApiTests.java                         (layer 2 — 7 contract tests)
        ├── FakeLlmClient.java, ThrowingLlmClient.java, DelegatingLlmClient.java
        └── evals/
            ├── CategorisationQualityTests.java   (layer 3 — 4 gates + a summary)
            └── (eval_dataset.json lives in src/test/resources/evals/)
```

`Core.java` is deliberately pulled apart into `buildPrompt`, `parseResponse`, `applyConfidenceThreshold` and `categorise`. That decomposition is not decoration — it is what makes layer 1 possible at all. Most AI features are hard to test because nobody separated the deterministic parts from the model call.

---

## Notes for the Java path

**No first-party Google GenAI SDK exists for Java that we want attendees to learn here**, so `GeminiClient.java` talks to the REST API through `java.net.http.HttpClient` — about 90 lines. Two settings there matter and are easy to miss: `responseMimeType: "application/json"` (ask for JSON rather than hoping) and `temperature: 0.1` (this is classification, not creativity).

**`LlmClient` is the seam everything hangs off**, same as the C# and TypeScript ports. Spring Boot has no direct equivalent of ASP.NET's `WebApplicationFactory`, which rebuilds the whole app per test — `ApiTests.java` instead shares one Spring context across the class and swaps a `DelegatingLlmClient`'s target fake before each HTTP call. Worth reading `ApiTests.java` for the pattern even if you skip the rest.

**The eval suite deliberately does not use that seam** — it constructs a real `GeminiClient`. That's the line between layer 2 and layer 3.

---

## Post-workshop

1. **Grow the dataset.** 22 cases is a fast CI loop, not a real eval set. Add the transactions your own users actually submit, especially the ambiguous ones.
2. **Add a nightly run.** PR evals should be fast; nightly evals can afford 200+ cases and tighter thresholds.
3. **Track drift over time.** Log accuracy per run and alert on the trend, not just the threshold. A model that degrades from 96% to 87% is still passing — and still worth knowing about.
