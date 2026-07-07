# Plan: <feature-name>

*Technical approach. Derived from the spec and clarifications; authored before any code.*

---

## Summary

One short paragraph. The one-liner a reviewer reads first.

---

## Approach

Which algorithm, library, or service does this rely on, and why?

- **Core technique**: e.g. collaborative filtering + content embeddings with a fallback rule-based layer.
- **Model / provider**: e.g. Anthropic Claude Sonnet 4.6 for the categorisation; Gemini 2.5 Flash for the lightweight scoring.
- **Why this over the alternatives**: e.g. benchmark comparison of Sonnet vs Haiku for our eval set; Haiku hit accuracy target at 1/3 the cost.

---

## Data flow

Describe the path an input takes, end-to-end.

1. User request arrives at the API.
2. API calls the context-building service.
3. Context + system prompt go to Anthropic.
4. Response is parsed; tool calls are routed to local tools.
5. Final response is logged (with model id, prompt hash, confidence) and returned to the user.

A small ASCII diagram often helps:

```
user ──▶ api ──▶ context-builder ──▶ model ──▶ tool-router ──▶ model ──▶ parser ──▶ api ──▶ user
                                       │                                          │
                                       └─────────── traces / logs ────────────────┘
```

---

## Integration points

Where this feature touches existing systems.

- **Reads from**: (e.g. users table, content library, feedback stream)
- **Writes to**: (e.g. recommendation_logs, user_preferences)
- **Events emitted**: (e.g. `recommendation.shown`, `recommendation.clicked`)
- **External APIs**: (e.g. Anthropic Claude, Gemini, Opik, Stripe)

---

## Eval strategy

How do the spec's thresholds turn into measurements?

- **Pre-deployment (runs on every PR)**:
  - `tests/evals/test_categorisation.py` — 200-case golden set. Block merge if accuracy <85%.
  - `tests/evals/test_catastrophic.py` — 50-case "must never" set. Block merge on any failure.
- **Production (runs continuously)**:
  - Hourly check: accuracy on last-1000 traces (Opik + LLM-as-judge).
  - Daily check: confidence distribution drift.
  - Weekly check: learning-phase CTR improvement across active users.
- **Human review sampling**: 10 random low-confidence traces per day → team review queue.

Refer to `templates/spec-template.md#acceptance-criteria-mapped-to-ce` — every line there should have a monitor here.

---

## Rollout strategy

- **Pre-launch**: evals green on main branch. Smoke test against 3 canary users.
- **Canary**: 5% of traffic for 24 hours. Watch auto-rollback triggers.
- **Gradual**: 5% → 25% → 100% over 5 days, with quality gates between each step.
- **Feature flag**: `recommendations_v2_enabled` — off by default, per-user override via admin.
- **Rollback trigger**: accuracy drops >10% within 1 hour, OR catastrophic-failure rate >0, OR p95 latency >2× baseline. Automatic, no human approval needed.
- **Graceful degradation**: on provider error, serve cached top-10 trending; show "popular right now" label.

---

## Risks and mitigations

Top 3–5 concrete risks that could sink the feature.

1. **Risk**: cold-start users get irrelevant recommendations → churn spike.
   **Mitigation**: curated onboarding sequence for first 5 sessions before personalisation kicks in. Monitor day-1 retention as the leading indicator.

2. **Risk**: LLM provider changes model behaviour silently (API stays same).
   **Mitigation**: pin model version. Run evals on a schedule independent of deploys. Alert on drift even when no code changed.

3. **Risk**: adversarial feedback (users gaming thumbs-down to steer recommendations).
   **Mitigation**: rate-cap feedback per user; content-integrity monitor that flags unusually-skewed feedback patterns.

4. **Risk**: cost runaway if each request hits Opus.
   **Mitigation**: Haiku for scoring, Opus for only the top-10 rerank. Workspace-level $ cap as a backstop.

5. **Risk**: personalisation becomes harder to reason about over time as the feedback corpus grows.
   **Mitigation**: quarterly review where a human samples 50 recommendations and judges relevance blind.

---

## Cost estimate

Rough per-user or per-request cost.

- **Cold-start**: ~$0.0005 per recommendation (Haiku only, small context).
- **Warm**: ~$0.003 per recommendation (Haiku + occasional Opus rerank).
- **100k DAU × 5 recommendations/day**: ≈ $1,500/day = ~$45k/month. Needs product buy-in before launch.

Caching (Anthropic prompt caching, 5-min TTL) on the system prompt + tool definitions cuts this by ~40%.

---

## Open questions

Things we'd want answered before implementing, but can live with open if time-boxed:

- Which embedding model for content similarity — OpenAI, Cohere, or Voyage? (Benchmark week 1.)
- How often to re-embed the content library? (Defer to week 2 once we have base case working.)
- Do we need PII redaction in logged prompts? (Legal to confirm.)

---

## Out of scope (for the plan)

- UI design — owned by the product team; spec references the API contract only.
- A/B experimentation platform integration — will use whatever the growth team recommends.
