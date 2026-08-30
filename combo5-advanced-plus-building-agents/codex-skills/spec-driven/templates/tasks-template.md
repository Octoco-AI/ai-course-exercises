# Tasks: <feature-name>

*Actionable breakdown of the plan. One task = one mergeable change, ~1–2 days of work. Ordered by dependency; unblocked tasks can start now.*

---

## Task conventions

- **Size**: each task is ~1–2 days. If larger, split. If smaller, combine.
- **Done-when**: each task has an explicit acceptance criterion. "Works on my machine" is not a criterion; a passing test or a running deployment is.
- **Dependencies**: if a task requires another to be complete, note `depends-on: #N`. Tasks with no dependencies are ready to start.
- **Owner**: to be filled in at sprint planning, not here.

---

## 1. Scaffold the recommendation service

**Description**: create the service module and health endpoint. No AI yet — stub the model call with a hard-coded response.

**Done-when**: `GET /recommendations/{user_id}` returns a 200 with three hard-coded items. CI green on `tests/test_recommendations_scaffold.py`.

**Depends-on**: none.

**Estimate**: 0.5 day.

---

## 2. Add the eval set foundation

**Description**: create `tests/evals/` with 30 seed eval cases mirroring the spec's acceptance criteria. DeepEval configured. `pytest tests/evals/` runs (will fail against the stub — expected).

**Done-when**: `deepeval test run tests/evals/` executes and produces a results report. CI workflow `.github/workflows/evals.yml` is drafted (runs on PR).

**Depends-on**: none.

**Estimate**: 1 day.

---

## 3. Integrate the LLM provider

**Description**: replace the stubbed response with a real Anthropic call. System prompt from `prompts/recommendations.md`. Tools: none for this phase. Response parsing with schema validation.

**Done-when**: `GET /recommendations/{user_id}` returns real AI-generated recommendations. Unit tests for prompt construction and response parsing. No eval-quality check yet.

**Depends-on**: #1.

**Estimate**: 1.5 days.

---

## 4. Wire evals into CI

**Description**: connect the eval set from #2 against the live model from #3. Fail-build threshold at accuracy <85%.

**Done-when**: a PR that deliberately breaks the prompt (e.g. "recommend random videos") is blocked by CI. Passing PR shows the eval report in the CI output.

**Depends-on**: #2, #3.

**Estimate**: 1 day.

---

## 5. Add confidence-threshold fallback

**Description**: implement the graceful degradation from the spec. When confidence <0.6, return "popular in similar situations" cached content. Monitor the fallback rate.

**Done-when**: integration test demonstrates the fallback triggers when the model returns low-confidence. Fallback rate metric emitted to Opik.

**Depends-on**: #3.

**Estimate**: 1 day.

---

## 6. Add feedback endpoint

**Description**: `POST /recommendations/{rec_id}/feedback` accepts explicit thumbs-up/down. Feedback is stored in `recommendation_feedback` table and emitted as an event.

**Done-when**: feedback round-trips end-to-end. Unit tests for validation (only the recipient user can submit feedback for their own recommendations). Event appears in the analytics stream.

**Depends-on**: #3.

**Estimate**: 1 day.

---

## 7. Production tracing with Opik

**Description**: instrument the service with Opik tracing. Session-ID grouping, tool-call spans, token and latency metrics.

**Done-when**: every recommendation request appears as a trace in Opik. Dashboard shows latency distribution, confidence distribution, and fallback rate.

**Depends-on**: #3, #5.

**Estimate**: 0.5 day.

---

## 8. Auto-rollback on eval regression

**Description**: CE pipeline that runs the eval suite against a sample of production traces every hour. If accuracy drops below 80%, trigger auto-rollback via feature flag.

**Done-when**: synthetic regression (a prompt change that tanks accuracy on purpose) auto-rolls-back within one hour window. Alert fires to the team channel.

**Depends-on**: #4, #7.

**Estimate**: 1.5 days.

---

## 9. Canary deploy and gradual rollout

**Description**: deploy behind the `recommendations_v2_enabled` feature flag. 5% canary for 24 hours. Watch rollback triggers.

**Done-when**: 5% of traffic served for 24 hours without triggering rollback. Metrics green.

**Depends-on**: #7, #8.

**Estimate**: 2 days (most of it monitoring).

---

## 10. Full rollout

**Description**: ramp 5% → 25% → 100% over 5 days.

**Done-when**: 100% of users on v2. v1 code path marked for deletion in the next sprint.

**Depends-on**: #9.

**Estimate**: 5 days wall-clock, ~0.5 day active work.

---

## Parallelisable work

These tasks have no dependencies on each other and can be worked in parallel:

- **After #1**: #2 (evals foundation) and #3 (LLM integration) can start in parallel.
- **After #3**: #5 (fallback) and #6 (feedback) can start in parallel.
- **After #4, #7**: #8 (auto-rollback) is sequential, but the runbooks for it can be drafted while #7 is in progress.

---

## Explicitly not in this list

- UI work — separate track owned by the product team.
- Content library expansion — separate.
- Moderator review queue — v2.1 feature, not blocking launch.
