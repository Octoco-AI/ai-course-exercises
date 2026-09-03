# Clarify checklist

Ambiguity patterns that bite AI specs. For each item, check the spec: does it have a clear
answer? If not, either propose one (with justification) or ask the user.

**Start with the PRD's own `## Open Questions`, carried into the spec verbatim from Phase 2
— address every one of those before working through the general patterns below.** They are
the PM's own list of what they know they don't know; the checklist below is what a lean PRD
never had a section to ask in the first place.

---

## On the user side

1. **Who, exactly?** The spec says "users" — but does every user get the same experience, or do different segments get different behaviour? (New vs returning, paid vs free, by role, by child's age, etc.)
2. **First-time experience vs steady state.** What does a brand-new user see before the AI has any data about them? (Cold-start is often the hardest case and the most under-specified.)
3. **What would frustrate them?** If the AI gets 80% of cases right, what do the other 20% feel like to the user? Silently-wrong is worse than obviously-not-sure.
4. **Where does the user hear about this feature?** Are they expecting AI behaviour, or will they be confused that it's AI? Does "powered by AI" appear in the UI?

---

## On the data side

5. **What drives the AI's decision?** Make the input explicit — which signals does the model see? Any data the spec doesn't name is either missing or implicit. Both are bugs.
6. **Where does that data live?** In the user's record? A separate profile service? An analytics event stream? Latency and availability of each source matters.
7. **What about PII?** Does the spec involve any data that's sensitive, regulated (HIPAA, GDPR, etc.), or attacker-interesting? If so, call out the data-handling rules.
8. **Data volume and freshness.** Does the AI need real-time data, or can it be stale by a day? Per-user or aggregated across users?

---

## On the AI side

9. **Which model and why?** The spec doesn't have to commit to a model, but the plan does. Is the choice driven by cost, latency, accuracy, compliance, or all four?
10. **Deterministic or probabilistic?** Some AI features want `temperature=0` (e.g. a classifier); others want some randomness (e.g. creative text). The spec should be explicit.
11. **Prompt stability.** Is the prompt versioned? Does a prompt change require a full eval re-run?
12. **Tool use or no?** If yes, which tools? What can each do? Which need human confirmation?

---

## On the confidence side

13. **What does "confidence" mean?** A probability from the model? A calibrated score from evals? Self-reported by the LLM (unreliable)? Derived from an ensemble? The spec should name the source.
14. **Threshold rationale.** Where did the confidence cutoff come from — user research, eval data, a gut feel? If it's gut feel, treat the first weeks in prod as a calibration period.
15. **Who sees the confidence?** Only logs? The user, as a visible indicator? The user only when low? Design implications differ.

---

## On the failure side

16. **What's the blast radius of a wrong answer?** Bad recommendation = annoyed user. Bad medical categorisation = real harm. The spec's mitigation effort should match.
17. **Adversarial users.** Is anyone incentivised to game the system? (E.g. users trying to get a higher credit line; SEO spam flooding a content scorer.)
18. **Model provider downtime.** Have you tested a 24-hour provider outage? What does the feature do?
19. **Silent degradation.** How would you notice the feature had started getting worse by 10% over 2 weeks? This is the hardest failure to detect.

---

## On the rollout side

20. **Launch slice.** How wide is the initial rollout — 100% of users, 5% canary, internal-only for a week?
21. **Rollback trigger.** What metric movement triggers automatic rollback? (See CE pipeline article.)
22. **A/B test needed?** Is there a clear null hypothesis and a measurable effect size?

---

## On ownership

23. **Who owns the eval suite?** If the feature degrades in prod, whose pager goes off?
24. **Who owns model upgrades?** When the provider releases a new model version, who decides whether to upgrade?
25. **Who signs off on the spec itself?** Eng, product, clinical (if applicable), legal (if applicable). If this spec traces back to a PRD, does the PM sign off on the spec too, or just the requirements they wrote?

---

## On the PRD gap — the group `spec-driven`'s checklist doesn't need

A lean PRD is written to be readable by a PM and a stakeholder, so it never mentions any of
these. That's correct for its job, not a defect — but it means every one of these is a real
gap here, not a "probably fine, skip it."

26. **Non-functional limits.** Concurrency, rate limits, request size caps — did the PRD's requirements imply a volume the system has to survive, without ever naming it?
27. **Retention and privacy.** How long is data kept? Deleted on request? A PRD requirement about "the member list" says nothing about how long a departed member's data lives.
28. **Authn/authz.** Who's allowed to trigger this feature, see its output, or override it? A PRD scenario assumes a logged-in user exists; it doesn't say who else can act on their behalf.
29. **Scale.** What load does this need to handle at launch, and in a year? A PRD goal like "reduce time to find X" says nothing about how many Xs.
30. **Error handling.** What does the user see, concretely, when the happy path breaks in a way that isn't one of the four extras' failure modes — a network error, a malformed input, a timeout unrelated to the AI call?
31. **Observability.** What gets logged or traced so someone can debug this in production? A PRD never mentions logging; someone still has to decide what's logged.
32. **Data migration.** Does shipping this change the shape of existing data? A PRD requirement about new behaviour says nothing about what happens to records that predate it.
33. **Accessibility.** Screen readers, keyboard navigation, colour contrast for anything the PRD's requirements imply gets a UI. A PRD's scenarios describe behaviour, not how it's rendered.

---

*Not every item applies to every feature. Skim fast; dwell on the ones that feel "oh we didn't think about that." Items 1–25 are `spec-driven`'s general checklist — keep working through them even after the PRD-specific group above, they still apply.*
