# Spec: <feature-name>

*The four-extras pattern, plus traceability back to the PRD this spec was drawn from. Every
section is required unless marked optional; don't skip any of the required ones.*

*This is `spec-driven`'s `spec-template.md` with two sections added — `Traceability` and
`Questions for the PRD author` — because this spec has a source document to stay honest
against. Everything else here is unchanged.*

---

## Context

*From the PRD's Problem and Who It Affects. Motivation, not a requirement — nothing here is
testable and nothing here belongs in the requirements list below.*

Example:
> Senior reviewers spend review time on PRs that turn out to have no substantive issues,
> while the PRs that do need close attention aren't distinguishable up front. The feature
> exists to redirect attention, not to replace review.

---

## Requirements

*Carried from the PRD's `## Requirements`, strength verb intact, restated wherever the
original failed the durability test (see `Traceability` below for which ones were).*

### <Requirement name>
The system SHALL/MUST/SHOULD/MAY <observable behaviour>.

#### Scenario: <names the case>
- GIVEN <precondition>
- WHEN <action>
- THEN <observable outcome>

---

## 1. Performance thresholds

Measurable criteria for success. At least one number per category. **`[NEW — not in PRD]`
unless the PM's Goals section already named a number, which is rare.**

- **Accuracy**: e.g. "Top-3 recommendations achieve >70% click-through in the user's first session."
- **Latency**: e.g. "Recommendations returned within 500ms (p95)."
- **Confidence**: e.g. "Only act on predictions with confidence > 0.75; below that, fall back to generic content."
- **Quality floor**: e.g. "Zero recommendations for archived or age-inappropriate content — this is a hard rule, not a threshold."

---

## 2. Graceful degradation

What happens when the AI can't deliver the ideal outcome. **`[NEW — not in PRD]`** — a lean
PRD's scenarios cover product edge cases, not system failure.

- **Fallback behaviour**: e.g. "If confidence <60%, show 'popular in similar situations' content instead of personalised results."
- **Partial results**: e.g. "If only 2 of 3 recommendations meet threshold, show those 2 + a 'getting-started' curated video."
- **Human handoff criteria**: e.g. "If confidence <40%, display a 'speak to a clinician' prompt instead of any AI output."
- **Availability fallback**: e.g. "If the LLM provider is down, serve cached trending content."

---

## 3. Learning expectations

How the system should improve over time. **`[NEW — not in PRD]`**

- **Feedback signals**: e.g. "Explicit: thumbs up/down on each recommendation. Implicit: video completion rate, time-to-first-click."
- **Adaptation timeline**: e.g. "Personalisation improves to >85% CTR after the user rates 5+ videos."
- **Personalisation scope**: e.g. "Per-user, per-child. No cross-family data sharing."
- **Retraining cadence**: e.g. "Weekly fine-tuning on last-30-days feedback, with the ability to pause if quality drops."

---

## 4. Failure modes

Bugs AI systems have that traditional software doesn't. **`[NEW — not in PRD]`** — distinct
from the PRD's own non-happy-path scenarios, which are product edge cases, not the specific
ways an AI system misbehaves.

- **False positives**: e.g. "Recommending a video that's age-inappropriate. Mitigation: hard filter on content tags before scoring."
- **False negatives**: e.g. "Missing a highly-relevant new video because it hasn't been tagged yet. Mitigation: editor-flagged 'featured' path that bypasses scoring."
- **Bias**: e.g. "Over-recommending videos about medication to parents of boys vs girls. Mitigation: demographic-parity monitor in CE pipeline."
- **Adversarial inputs**: e.g. "Malicious user floods thumbs-down to poison the recommendation. Mitigation: per-user rate cap, content integrity checks."

---

## Acceptance criteria (mapped to CE)

These are the exact criteria that become continuous-evaluation gates in production. Every
line here corresponds to a monitor in the CE pipeline. The scenarios carried from the PRD's
requirements are acceptance criteria too — list them alongside the ones the four extras add.

- [ ] Top-3 CTR >70% (primary eval, runs on every PR).
- [ ] Recommendation latency p95 <500ms (perf eval, runs on canary).
- [ ] Confidence distribution: >75% of outputs have confidence >0.75 (drift check, runs hourly in prod).
- [ ] Zero age-inappropriate outputs across 500-case eval set (catastrophic-failure gate, blocks merge).
- [ ] Post-5-ratings CTR >85% (learning check, runs weekly on prod data).

---

## Out of scope

*Carried from the PRD's `## Scope` → Out of scope, verbatim, with its stated reason.*

- Does not send notifications (separate feature).
- Does not support non-English content (future iteration).
- Does not affect the clinician-view of the data (clinician dashboard is unchanged).

---

## Traceability

One row per spec item: where it came from, and whether it was carried, added, or a stated
gap. This is what makes the handoff auditable — the PM should be able to read this table and
know exactly what they decided versus what engineering decided.

| Spec item | PRD source | Status |
|---|---|---|
| <requirement name> | PRD `## Requirements` | Carried |
| <requirement name> | PRD `## Requirements` (originally named an implementation detail) | Carried, restated for durability |
| <extra, e.g. a performance threshold> | — | `[NEW — not in PRD]` |
| <What's There Today claim used to ground a requirement> | PRD `## What's There Today` | Verified / Contradicted / Could not verify |

## Questions for the PRD author

Anything that surfaced while writing this spec that the PM should weigh in on — a
requirement that only became ambiguous once it had to be made testable, or a plan-stage
decision (once Phase 4 runs) that constrains or contradicts something the PRD said. Omit
this section if there's genuinely nothing to send back.

- <question, one line, addressed to whoever wrote the PRD>
