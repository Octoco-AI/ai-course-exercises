---
name: spec-driven
description: Walk through the constitution → specify → clarify → plan → tasks flow for a new AI feature. Use when the user asks to "spec out" a feature, asks to "spec-drive" work, or is starting any AI-touching feature before coding. Pauses between phases for user review.
---

# Spec-driven development

Work through the five phases of spec-driven development for an AI feature. **Pause after each phase. Present the output. Ask the user to approve before moving to the next phase.** Do not chain phases.

This skill exists because specifications matter more when the thing you're building has non-deterministic behaviour. Performance thresholds, graceful degradation, learning expectations, and failure modes are what turn "we think the AI categorised this correctly" into "we know the AI hit our agreed 85% bar on the acceptance suite."

## The feature

The feature is whatever the user named in the message that invoked this skill — e.g. "personalised video recommendations".

If they invoked the skill with no feature named, ask: *"What feature are we specifying? Give me a short description — one or two sentences is enough."*

## State detection

Look at what already exists before choosing a phase:

1. `./AGENTS.md` present with a `## Constitution` heading? → Phase 1 is done.
2. `./specs/<feature-slug>.md` present? → Phase 2 is done.
3. `./specs/<feature-slug>.md` has a `## Clarifications` heading? → Phase 3 is done.
4. `./plans/<feature-slug>.md` present? → Phase 4 is done.
5. `./tasks/<feature-slug>.md` present? → Phase 5 is done.

Resume at the first undone phase. Tell the user which phase you're starting and why.

The feature slug is the feature name, lowercased, with spaces replaced by hyphens (e.g. "video recommendations" → `video-recommendations`).

---

## Phase 1 — Constitution (project rules)

**Purpose**: establish the rules every AI feature in this project must follow. These go into `AGENTS.md` so Codex reads them at the start of every session.

**Do:**
1. Check for `./AGENTS.md`. If it exists and has a `## Constitution` section, read it and skip to Phase 2.
2. If it doesn't exist, ask the user about their project's AI feature principles. Use `templates/constitution-template.md` as the prompt skeleton. Topics to ask about:
   - Architecture (stack, patterns).
   - AI-specific principles (confidence indicators, graceful degradation, audit requirements, feedback mechanisms).
   - Never-do items (no medical claims without review, no decisions without human approval, etc.).
   - Delegation norms.
3. Draft the constitution section and show it to the user. Ask: *"Does this capture your project's rules, or should we adjust?"*
4. On approval, write it to `./AGENTS.md`. If an `AGENTS.md` already exists at the project root, ask where the user wants the constitution section added — Codex reads the whole file, so ordering is a readability choice, not a functional one.

**Stop. Summarise what you did. Ask the user whether to continue to Phase 2.**

---

## Phase 2 — Specify (the user story)

**Purpose**: capture WHAT the feature does, with measurable acceptance criteria that include AI-specific uncertainty.

**Do:**
1. Read the constitution from Phase 1 to ground your work in the project's rules.
2. Draft a user story using the four-extras pattern from `templates/spec-template.md`:
   - **Traditional**: As a [user], I want [feature], so that [benefit].
   - **Performance thresholds**: accuracy, latency, confidence.
   - **Graceful degradation**: fallback behaviours, partial results, human-handoff.
   - **Learning expectations**: feedback signals, adaptation timeline, personalisation scope.
   - **Failure modes**: false positives, false negatives, bias, adversarial inputs.
3. For each of the four extras, **ask the user for specifics**. Do not invent numbers. If the user says "I don't know," help them reason about it (e.g. for accuracy, ask what unacceptable looks like — that bounds the target).
4. Write the spec to `./specs/<feature-slug>.md`.

**Stop. Show the spec. Ask the user to approve or revise before Phase 3.**

---

## Phase 3 — Clarify (surface ambiguities before planning)

**Purpose**: the biggest cause of spec failure is unexamined ambiguity. Find and resolve it before investing in a plan.

**Do:**
1. Read the Phase 2 spec.
2. Walk through `templates/clarify-checklist.md` — a list of common ambiguity patterns (what "personalised" means, what data drives learning, who sees confidence scores, etc.). For each item the spec doesn't clearly answer:
   - **Propose** an answer with justification, OR
   - **Ask** a direct question if you can't propose a sensible default.
3. Record all clarifications in a `## Clarifications` section appended to `./specs/<feature-slug>.md`. Preserve the original spec text; don't overwrite.

**Stop. Summarise what was clarified and what remains open. Ask the user to confirm before Phase 4.**

---

## Phase 4 — Plan (technical approach)

**Purpose**: decide HOW to build it, without yet touching code.

**Do:**
1. Read the Phase 2 spec and Phase 3 clarifications.
2. Draft a plan using `templates/plan-template.md`. Cover:
   - **Approach**: algorithm / library choice, provider, model tier.
   - **Data flow**: where inputs come from, where outputs go, what's logged.
   - **Eval strategy**: how we'll measure the performance thresholds from the spec. Which evals run in CI, which run in production.
   - **Rollout strategy**: canary / feature flag / A/B / graceful degradation.
   - **Risks and mitigations**: 3–5 concrete risks with responses.
3. Write the plan to `./plans/<feature-slug>.md`.

**Stop. Show the plan. Ask the user to approve or revise before Phase 5.**

---

## Phase 5 — Tasks (actionable breakdown)

**Purpose**: turn the plan into individually-deliverable work items.

**Do:**
1. Read the plan.
2. Break it into tasks using `templates/tasks-template.md`. Each task must be:
   - **Independently deliverable** — one task = one mergeable change.
   - **Testable** — there's a way to know the task is done.
   - **Sized for ~1–2 days of work** — if longer, split.
   - **Ordered** — dependencies listed, so the team knows what can start now and what must wait.
3. Write the task list to `./tasks/<feature-slug>.md`.

**Stop. Show the tasks. Offer to kick off the first task if the user is ready.**

---

## Finishing

Summarise what exists after this session:

- `./AGENTS.md` with the project constitution
- `./specs/<feature-slug>.md` — user story + clarifications
- `./plans/<feature-slug>.md` — technical plan
- `./tasks/<feature-slug>.md` — actionable tasks

Suggest next steps:

- Commit these files to the repo.
- Share the plan with the team before starting implementation.
- When starting implementation, dispatch a sub-agent (`.codex/agents/<name>.toml`) or invoke your implementation skill — the constitution is loaded from `AGENTS.md` on every session, and the spec, plan and tasks are on disk for the agent to read.

## Principles to hold throughout

- **You draft, the human approves.** Every artefact this skill produces should be reviewed. Don't try to close a phase the user hasn't looked at.
- **Cite the constitution.** If a choice in the plan contradicts the constitution, call it out and ask.
- **No code in this skill.** If the user asks for code, redirect: "Let's finish the spec first. Code happens after Phase 5."
- **Be honest about uncertainty.** If a performance threshold is a guess, say so. Don't present guesses as known facts.
