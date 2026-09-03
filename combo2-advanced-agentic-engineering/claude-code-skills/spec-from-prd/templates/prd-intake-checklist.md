# PRD intake checklist

A lean PRD (`write-lean-prd`'s output shape) is a complete, honest document for what it's
for — a PM decision record. It is not an engineering spec, and it was never meant to be one.
This checklist is how Phase 0 reads it: section by section, what to carry forward untouched,
what to verify, and what the PRD structurally cannot contain — which is exactly the list
Phase 2 has to fill in with the user, not invent.

Worked throughout against the sample PRD in `../../example-prd.md` (AI-Assisted PR Review
Triage) so every row has a concrete instance, not just a rule.

---

## Section by section

### `# PRD: <Title>` and `## Problem` / `## Who It Affects`

Motivation, never a requirement. Carry it into the spec's context, not its requirements
list. If the PRD says the Problem section is "unevidenced" (its own honesty convention when
questioning was cut short), say so in the intake report — it's a signal the spec's numbers
will be softer than usual, not something to paper over.

*Example*: "senior engineers spend review time on trivial PRs" is why the feature exists.
It is not testable and does not become a requirement.

### `## What Changes`

One paragraph, plain language. This is your spec's one-line summary — compress it further
if you need to, but don't reinterpret it. If what you'd write as the summary doesn't match
what the requirements actually do, that's a sign the PRD and its requirements have drifted
apart — flag it, don't silently pick one.

### `## Goals`

Outcomes, not outputs, and not numbers. A goal like "reviewers trust the tool's flags" tells
you *what a threshold in Phase 2 is trying to protect* — it does not supply the threshold.
Read every goal and ask yourself: if I had to write a performance threshold, a graceful
degradation, a learning expectation or a failure mode that serves this goal, what would I
ask the user? Bring that question to Phase 2; don't answer it here.

### `## Scope`

**In scope** bounds the requirement set — anything you'd add beyond it needs the user's
sign-off first, even if it looks obviously necessary from an engineering point of view.

**Out of scope**, with its stated reason, becomes the spec's `## Out of scope` verbatim.
Treat every out-of-scope line as a constraint on the plan too: if a plan choice in Phase 4
would require touching something the PRD explicitly excluded, that's a `## Questions for the
PRD author` item, not a quiet scope creep.

### `## Requirements`

Each `### <name>` + strength verb + `#### Scenario:` block carries forward as a functional
requirement, **after one check**: does it survive `write-lean-prd`'s own durability test —
*would this still be true if the same thing were built a different way?* The skill that
produced this PRD tries hard to keep implementation out of requirements, but it isn't
infallible, and a requirement that named a table, an endpoint, a webhook, or a specific
vendor slipped through anyway. Restate it in observable terms before it becomes an
engineering requirement, and say so in `## Traceability` — the PM should see that a
requirement changed shape, not just that it "carried over."

*Example, straight out of `write-lean-prd`'s own guardrails*: "The system SHALL write a row
to the `pull_request_reviews` table for every triage comment it posts" fails the test — a
rewrite that used an event stream instead of a table would break it for no product reason.
Restate as: "A record of every triage comment posted exists and is retrievable by PR." Same
requirement, survives a rewrite.

Scenarios (GIVEN/WHEN/THEN) map straight onto acceptance-criteria lines in the spec. Keep
them; they're already testable.

### `## What's There Today`

This section is explicitly labelled "Unverified, check against the system before relying on
it" — take that literally. Check each claim against the Phase 0 repo read and mark it:

- **verified** — the repo confirms it.
- **contradicted** — the repo says something different. State what, and flag it loudly; a
  wrong assumption here can quietly invalidate a requirement built on top of it.
- **could not verify** — the repo doesn't say either way. Still unverified; still not a fact
  a requirement can depend on.

*Example*: a claim that "the monorepo is on GitHub Enterprise Server" is a one-command check
(`git remote -v`, or the CI config's runner). Don't skip it because it seems unimportant —
the plan's integration points in Phase 4 depend on it being right.

**Never let a claim from this section become a requirement, verified or not.** It describes
today, not what the feature must do.

### `## Open Questions`

Carry these into Phase 3 **verbatim, unanswered**. They are the PM's own list of what they
know they don't know. Answering one silently while drafting the spec is the exact failure
this skill exists to avoid — even a good-faith, obviously-correct-sounding answer takes a
decision away from the person who's supposed to make it.

---

## What a lean PRD structurally cannot tell you

Not a defect in the PRD — outside its job. Bring these to the user in Phase 2 as genuinely
new questions, and mark whatever you add `[NEW — not in PRD]`:

- **Performance thresholds** — accuracy, latency, confidence. A PRD goal names the outcome;
  it never names the number.
- **Graceful degradation** — what happens when the AI can't deliver the ideal outcome, or
  the provider is down. A PRD's scenarios cover the happy and unhappy *product* paths, not
  system failure.
- **Learning expectations** — feedback signals, adaptation timeline, personalisation scope.
- **Failure modes** — false positives, false negatives, bias, adversarial inputs. Distinct
  from the PRD's own non-happy-path scenarios, which describe product edge cases, not the
  ways an AI system specifically breaks.
- **Non-functional constraints** — retention, privacy, authn/authz, scale, observability,
  data migration, accessibility. None of these are product decisions; all of them need an
  engineering answer before Phase 4 can plan anything.

---

## Writing the intake report

One short paragraph per section above: what carried forward as-is, what needs verification
and against what, and which of the "structurally cannot tell you" items are genuinely absent
here and will need the user in Phase 2. This is what Phase 0 stops on — the user should be
able to read it and know exactly what they're about to be asked, before you ask it.
