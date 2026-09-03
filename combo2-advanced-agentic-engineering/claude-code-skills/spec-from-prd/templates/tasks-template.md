# Tasks: <feature-name>

*Actionable breakdown of the plan. One task = one mergeable change, ~1–2 days of work.
Ordered by dependency; unblocked tasks can start now. Same conventions as `spec-driven`'s
tasks template, plus a `Traces-to:` field per task — because a spec that traces back to a
PRD deserves tasks that trace back to the spec.*

---

## Task conventions

- **Size**: each task is ~1–2 days. If larger, split. If smaller, combine.
- **Done-when**: each task has an explicit acceptance criterion. "Works on my machine" is not a criterion; a passing test or a running deployment is.
- **Dependencies**: if a task requires another to be complete, note `depends-on: #N`. Tasks with no dependencies are ready to start.
- **Traces-to**: the spec requirement, extra, or clarification this task implements — e.g. `spec §Requirements → Ranked issue list`, or `spec §2 Graceful degradation`. A task with no trace is a task nobody asked for in the spec; flag it under "Explicitly not in this list" reasoning rather than dropping it silently — it might be genuine supporting infrastructure the spec didn't need to name.
- **Owner**: to be filled in at sprint planning, not here.

---

## 1. Scaffold the triage service

**Description**: create the service module and health endpoint. No AI yet — stub the review call with a hard-coded triage comment.

**Done-when**: opening a PR against the monorepo triggers a stub comment with three hard-coded findings. CI green on `tests/test_triage_scaffold.py`.

**Traces-to**: spec §Requirements → Automatic triage on PR open.

**Depends-on**: none.

**Estimate**: 0.5 day.

---

## 2. Add the eval set foundation

**Description**: create `tests/evals/` with 30 seed eval cases mirroring the spec's acceptance criteria — a mix of PRs that should be "safe to skim" and PRs with planted issues at each severity. DeepEval configured. `pytest tests/evals/` runs (will fail against the stub — expected).

**Done-when**: `deepeval test run tests/evals/` executes and produces a results report. CI workflow `.github/workflows/evals.yml` is drafted (runs on PR).

**Traces-to**: spec §1 Performance thresholds.

**Depends-on**: none.

**Estimate**: 1 day.

---

## 3. Integrate the LLM reviewer

**Description**: replace the stubbed response with a real Anthropic call over the PR diff. System prompt from `prompts/triage.md`. Response parsing with schema validation — issues, ranks, and the skim/read-closely label.

**Done-when**: opening a real PR produces a genuine ranked triage comment. Unit tests for prompt construction and response parsing. No eval-quality check yet.

**Traces-to**: spec §Requirements → Ranked issue list; Skim-vs-read-closely recommendation.

**Depends-on**: #1.

**Estimate**: 1.5 days.

---

## 4. Wire evals into CI

**Description**: connect the eval set from #2 against the live reviewer from #3. Fail-build threshold per the spec's performance thresholds.

**Done-when**: a PR that deliberately degrades the prompt (e.g. "flag everything as high-severity") is blocked by CI. Passing PR shows the eval report in the CI output.

**Traces-to**: spec §1 Performance thresholds; spec §Acceptance criteria.

**Depends-on**: #2, #3.

**Estimate**: 1 day.

---

## 5. Add provider-downtime fallback

**Description**: implement the graceful degradation from the spec. When the LLM provider is unavailable or times out, the PR gets a placeholder comment saying it wasn't reviewed rather than silence. Monitor the fallback rate.

**Done-when**: integration test demonstrates the fallback triggers on a simulated provider outage. Fallback rate metric emitted to the tracing tool named in the plan.

**Traces-to**: spec §2 Graceful degradation.

**Depends-on**: #3.

**Estimate**: 1 day.

---

## 6. Add reviewer feedback capture

**Description**: capture, per triage comment, whether the assigned reviewer acted on each flagged issue (resolved it, dismissed it, or ignored it). Feeds the learning-expectation cadence from the spec.

**Done-when**: feedback round-trips end-to-end. Event appears in the analytics stream.

**Traces-to**: spec §3 Learning expectations.

**Depends-on**: #3.

**Estimate**: 1 day.

---

## 7. Production tracing

**Description**: instrument the service per the plan's eval strategy — session grouping, per-PR spans, token and latency metrics.

**Done-when**: every triage run appears as a trace in the tool named in the plan. Dashboard shows latency distribution, false-positive-rate trend, and fallback rate.

**Traces-to**: spec §Acceptance criteria (drift check).

**Depends-on**: #3, #5.

**Estimate**: 0.5 day.

---

## 8. Auto-rollback on eval regression

**Description**: CE pipeline that runs the eval suite against a sample of production PRs on a schedule. If the false-positive rate crosses the spec's threshold, trigger auto-rollback via feature flag.

**Done-when**: a synthetic regression (a prompt change that tanks precision on purpose) auto-rolls-back within the plan's stated window. Alert fires to the team channel.

**Traces-to**: spec §1 Performance thresholds; plan §Rollout strategy.

**Depends-on**: #4, #7.

**Estimate**: 1.5 days.

---

## 9. Canary rollout

**Description**: deploy behind a feature flag per the plan's rollout strategy. Small canary slice first. Watch rollback triggers.

**Done-when**: the canary slice runs for the plan's stated window without triggering rollback. Metrics green.

**Traces-to**: plan §Rollout strategy.

**Depends-on**: #7, #8.

**Estimate**: 2 days (most of it monitoring).

---

## 10. Full rollout

**Description**: ramp to 100% per the plan's stated schedule.

**Done-when**: 100% of PRs on the monorepo get triage. Old manual-only path documented as no longer the default.

**Traces-to**: plan §Rollout strategy.

**Depends-on**: #9.

**Estimate**: matches the plan's rollout schedule.

---

## Parallelisable work

These tasks have no dependencies on each other and can be worked in parallel:

- **After #1**: #2 (evals foundation) and #3 (LLM integration) can start in parallel.
- **After #3**: #5 (fallback) and #6 (feedback capture) can start in parallel.
- **After #4, #7**: #8 (auto-rollback) is sequential, but the runbooks for it can be drafted while #7 is in progress.

---

## Explicitly not in this list

- Reviewing PRs on any repo other than the core monorepo — out of scope in the PRD (`## Scope` → Out of scope), not deferred here.
- Inline suggested-fix diffs — out of scope in the PRD.
- Anything that would auto-approve or auto-merge a PR — explicitly ruled out in the PRD and restated as a never-do item in the constitution.
