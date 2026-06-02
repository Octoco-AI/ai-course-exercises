# Spec: <feature-name>

*The four-extras pattern. Every section is required; don't skip any.*

---

## Traditional user story

> As a [user / role],
> I want [feature],
> So that [benefit].

Example:
> As a parent managing my child's ADHD,
> I want video recommendations personalised to my family's current challenges,
> So that I can quickly find relevant guidance without searching.

---

## 1. Performance thresholds

Measurable criteria for success. At least one number per category.

- **Accuracy**: e.g. "Top-3 recommendations achieve >70% click-through in the user's first session."
- **Latency**: e.g. "Recommendations returned within 500ms (p95)."
- **Confidence**: e.g. "Only act on predictions with confidence > 0.75; below that, fall back to generic content."
- **Quality floor**: e.g. "Zero recommendations for archived or age-inappropriate content — this is a hard rule, not a threshold."

---

## 2. Graceful degradation

What happens when the AI can't deliver the ideal outcome.

- **Fallback behaviour**: e.g. "If confidence <60%, show 'popular in similar situations' content instead of personalised results."
- **Partial results**: e.g. "If only 2 of 3 recommendations meet threshold, show those 2 + a 'getting-started' curated video."
- **Human handoff criteria**: e.g. "If confidence <40%, display a 'speak to a clinician' prompt instead of any AI output."
- **Availability fallback**: e.g. "If the LLM provider is down, serve cached trending content."

---

## 3. Learning expectations

How the system should improve over time.

- **Feedback signals**: e.g. "Explicit: thumbs up/down on each recommendation. Implicit: video completion rate, time-to-first-click."
- **Adaptation timeline**: e.g. "Personalisation improves to >85% CTR after the user rates 5+ videos."
- **Personalisation scope**: e.g. "Per-user, per-child. No cross-family data sharing."
- **Retraining cadence**: e.g. "Weekly fine-tuning on last-30-days feedback, with the ability to pause if quality drops."

---

## 4. Failure modes

Bugs AI systems have that traditional software doesn't.

- **False positives**: e.g. "Recommending a video that's age-inappropriate. Mitigation: hard filter on content tags before scoring."
- **False negatives**: e.g. "Missing a highly-relevant new video because it hasn't been tagged yet. Mitigation: editor-flagged 'featured' path that bypasses scoring."
- **Bias**: e.g. "Over-recommending videos about medication to parents of boys vs girls. Mitigation: demographic-parity monitor in CE pipeline."
- **Adversarial inputs**: e.g. "Malicious user floods thumbs-down to poison the recommendation. Mitigation: per-user rate cap, content integrity checks."

---

## Acceptance criteria (mapped to CE)

These are the exact criteria that become continuous-evaluation gates in production. Every line here corresponds to a monitor in the CE pipeline.

- [ ] Top-3 CTR >70% (primary eval, runs on every PR).
- [ ] Recommendation latency p95 <500ms (perf eval, runs on canary).
- [ ] Confidence distribution: >75% of outputs have confidence >0.75 (drift check, runs hourly in prod).
- [ ] Zero age-inappropriate outputs across 500-case eval set (catastrophic-failure gate, blocks merge).
- [ ] Post-5-ratings CTR >85% (learning check, runs weekly on prod data).

---

## Out of scope

What this feature explicitly does NOT do. Prevents scope creep and documents the boundary for reviewers.

- Does not send notifications (separate feature).
- Does not support non-English content (future iteration).
- Does not affect the clinician-view of the data (clinician dashboard is unchanged).
