---
name: spec-from-prd
description: Turn a product PRD — typically one drafted with the write-lean-prd skill — plus any design artefacts and notes into an engineering spec with teeth, then clarify, plan and tasks. Use when a PM has handed you a PRD and you need requirements an agent can build against. Drafts the constitution from the PRD first if the project has none. Pauses between phases for user review.
disable-model-invocation: true
allowed-tools: Read Write Edit Grep Glob Bash(mkdir:*) Bash(ls:*)
argument-hint: "[path-to-prd-or-feature-name]"
---

# Spec from a PRD

Work through six phases — intake, constitution, specify, clarify, plan, tasks — to turn a product PRD into an engineering spec an agent can build against. **Pause after each phase. Present the output. Ask the user to approve before moving to the next phase.** Do not chain phases.

This skill exists because a lean PRD (the kind `write-lean-prd` produces) is deliberately thin on engineering concerns. It states observable behaviour with strength verbs and Given/When/Then scenarios — that's the right shape for a PM to write and a stakeholder to read. It has no performance thresholds, no graceful degradation, no learning expectations, no failure modes, because those aren't product decisions. That's not a gap in the PRD; it's the handoff. This skill's job is to carry every product decision forward untouched, and make the engineering decisions explicit rather than inventing them silently.

## The PRD

`$ARGUMENTS` is a path to the PRD file, or a feature name if the PRD isn't named yet.

1. If `$ARGUMENTS` is a path that exists, read it.
2. If `$ARGUMENTS` is a bare name, or empty, look for a PRD before asking:
   - Glob `./docs/`, `./`, `./product/`, and `./.claude/prd/` for a markdown file whose first line matches `# PRD:`.
   - Exactly one match → use it, and tell the user which file you picked.
   - Multiple matches → list them and ask which one.
   - No match → ask: *"Point me at the PRD — a file path, or paste it and I'll save it."* If they paste text, save it verbatim before continuing.
3. If what you're given isn't a PRD at all (no `# PRD:` title, no Problem/Scope/Requirements shape), say so and suggest `/spec-driven` instead — that skill starts a spec from nothing. Don't try to force this skill's phases onto a document that isn't a PRD.

The feature slug comes from the PRD's title: strip the `PRD: ` prefix, lowercase, spaces to hyphens (e.g. "PRD: AI-Assisted PR Review Triage" → `ai-assisted-pr-review-triage`).

## State detection

Look at what already exists before choosing a phase:

0. `./.claude/specs/<feature-slug>.prd.md` present? → Phase 0 is done.
1. `./CLAUDE.md` or `./.claude/CLAUDE.md` present with a `## Constitution` heading? → Phase 1 is done.
2. `./.claude/specs/<feature-slug>.md` present? → Phase 2 is done.
3. `./.claude/specs/<feature-slug>.md` has a `## Clarifications` heading? → Phase 3 is done.
4. `./.claude/plans/<feature-slug>.md` present? → Phase 4 is done.
5. `./.claude/tasks/<feature-slug>.md` present? → Phase 5 is done.

Resume at the first undone phase. Tell the user which phase you're starting and why.

These are the same artefact paths `spec-driven` uses (minus the frozen PRD copy, which is new here). A feature specified with this skill can be resumed with `/spec-driven <feature>` and vice versa — the state detection in both skills reads the same files.

---

## Phase 0 — Intake (read before you draft)

**Purpose**: know exactly what the PRD hands you, what it deliberately leaves out, and what the repo can confirm or contradict, before writing a single requirement.

**Do:**
1. Freeze the PRD: copy it verbatim to `./.claude/specs/<feature-slug>.prd.md` (create `./.claude/specs/` if needed). Never edit this copy — the PM's own document may keep changing; this frozen copy is what the spec traces against.
2. Ask what else exists: designs, screenshots, a linked doc, tickets, prior notes. Read anything the user points at. Don't go looking on your own initiative and don't ask them to connect anything that isn't already at hand.
3. Read the repo *bounded* — README, docs, obviously product-facing code paths. Enough to know what exists today. No source-tree crawl.
4. Walk `templates/prd-intake-checklist.md` against the PRD you were handed. It tells you, section by section, what to carry forward as-is, what to verify, and what the PRD structurally cannot contain — which is exactly what Phase 2 has to supply.
5. Write the intake report: what's carried forward, what's flagged for verification, which of the four engineering extras (performance thresholds, graceful degradation, learning expectations, failure modes) are genuinely absent and will need the user's input in Phase 2.

**Stop. Show the intake report. Ask the user to confirm before Phase 1.**

---

## Phase 1 — Constitution (project rules)

**Purpose**: establish the rules every AI feature in this project must follow, derived from the PRD where possible rather than interviewed from scratch.

**Do:**
1. Check for `./CLAUDE.md` and `./.claude/CLAUDE.md`. If either has a `## Constitution` section, read it and skip to Phase 2.
2. If neither exists, draft one from what you actually have, using `templates/constitution-template.md`:
   - **Architecture** — from the repo read in Phase 0 and any `What's There Today` claims in the PRD.
   - **Never-do items** — from the PRD's `Out of scope` bullets and any MUST NOT requirements.
   - **AI feature principles** — from the PRD's Goals and any confidence or fallback language already in its requirements.
   - **Delegation norms** — a PRD cannot tell you this. Ask.
3. Label the source of every line you draft: `[derived from PRD §Out of scope]`, `[from repo]`, `[assumed — confirm]`. Never present a derived line as if the PM stated it directly.
4. Show the draft. Ask: *"Does this capture your project's rules, or should we adjust?"*
5. On approval, write it to `./.claude/CLAUDE.md` (create the directory if needed). If a CLAUDE.md already exists at the project root, ask where the user wants the constitution section added.

**Stop. Summarise what you did. Ask the user whether to continue to Phase 2.**

---

## Phase 2 — Specify (the engineering spec)

**Purpose**: turn the PRD's product decisions into an engineering spec with teeth, without inventing the engineering decisions the PRD never made.

**Do:**
1. Read the frozen PRD, the intake report, and the constitution.
2. Work through `templates/prd-to-spec-map.md` — it maps every PRD section to where it lands in the spec. In outline:
   - **Problem, Who It Affects** → context only, never a requirement.
   - **What Changes** → the spec's one-line summary.
   - **Goals** → candidate performance thresholds. A goal is an outcome ("reviewers trust the tool's flags"), not a number — ask the user for the number that would tell you the goal was met.
   - **Scope → In scope** → the requirement set's boundary.
   - **Scope → Out of scope** → the spec's `## Out of scope`, kept verbatim with its stated reason.
   - **Requirements** (`### name` + SHALL/MUST/SHOULD/MAY + `#### Scenario:` GIVEN/WHEN/THEN) → carried forward as functional requirements, strength verb intact, each scenario becoming an acceptance-criteria line. **Before carrying one forward, apply the PRD's own durability test**: would it still hold if built a different way? A requirement that names a table, an endpoint, or a specific vendor failed that test even though `write-lean-prd` tries to prevent it — restate it in observable terms and note in `## Traceability` that you did.
   - **What's There Today** → each claim gets checked against the repo from Phase 0 and marked `verified`, `contradicted`, or `could not verify`. Never promote an unverified claim into a requirement.
   - **Open Questions** → carried into Phase 3 verbatim. **Do not answer them here.** Answering a PM's open question on their behalf is exactly the failure this skill exists to avoid.
3. For each of the four extras — performance thresholds, graceful degradation, learning expectations, failure modes — from `templates/spec-template.md`, **ask the user for specifics**. Do not invent numbers. Mark every extra you add `[NEW — not in PRD]`, because it wasn't a product decision the PM made; it's an engineering decision this phase is making, and the PM should see that split when they read the spec back.
4. Fill in `## Traceability` — one row per spec item: the PRD source (or "NEW"), and whether it's carried, added, or a stated gap.
5. Fill in `## Questions for the PRD author` — anything you found while specifying that the PM should weigh in on (a requirement that turned out ambiguous once made testable, a scope edge the PRD didn't anticipate).
6. Write the spec to `./.claude/specs/<feature-slug>.md`.

**Stop. Show the spec. Ask the user to approve or revise before Phase 3.**

---

## Phase 3 — Clarify (surface ambiguities before planning)

**Purpose**: the biggest cause of spec failure is unexamined ambiguity — and this PRD already told you where some of it is.

**Do:**
1. Read the Phase 2 spec.
2. Start with the PRD's own `## Open Questions`, carried verbatim from Phase 2 — these are not optional extras, they're ambiguities the PM already flagged. Address every one before moving to anything new.
3. Walk `templates/clarify-checklist.md` — `spec-driven`'s 25 general ambiguity patterns, plus a PRD-specific group covering the things a lean PRD structurally never states (non-functional limits, retention and privacy, authn/authz, scale, error handling, observability, data migration, accessibility). For each item the spec doesn't clearly answer: **propose** an answer with justification, or **ask** if you can't propose one sensibly.
4. Record all clarifications — the PRD's open questions and the checklist findings alike — in a `## Clarifications` section appended to `./.claude/specs/<feature-slug>.md`. Preserve the original spec text; don't overwrite.

**Stop. Summarise what was clarified and what remains open. Ask the user to confirm before Phase 4.**

---

## Phase 4 — Plan (technical approach)

**Purpose**: decide HOW to build it. This is where implementation detail belongs — not smuggled into a requirement in Phase 2.

**Do:**
1. Read the Phase 2 spec and Phase 3 clarifications.
2. Draft a plan using `templates/plan-template.md`: approach, data flow, integration points, eval strategy (how the spec's thresholds get measured), rollout strategy, 3–5 risks and mitigations.
3. If a plan decision constrains or contradicts a PRD requirement — a technical limit the PM didn't know about, a rollout choice that changes what "done" looks like — append it to `## Questions for the PRD author` in the spec rather than quietly overriding the requirement.
4. Write the plan to `./.claude/plans/<feature-slug>.md`.

**Stop. Show the plan. Ask the user to approve or revise before Phase 5.**

---

## Phase 5 — Tasks (actionable breakdown)

**Purpose**: turn the plan into individually-deliverable work items, each traceable back to why it exists.

**Do:**
1. Read the plan.
2. Break it into tasks using `templates/tasks-template.md`. Each task must be independently deliverable, testable, sized for ~1–2 days, and ordered by dependency.
3. Give each task a `Traces-to:` line — the spec requirement or extra it implements. A task with no trace is a task nobody asked for; flag it rather than dropping it silently, in case it's genuine infrastructure work the spec didn't need to name.
4. Write the task list to `./.claude/tasks/<feature-slug>.md`.

**Stop. Show the tasks. Offer to kick off the first task if the user is ready.**

---

## Finishing

Summarise what exists after this session:

- `./.claude/specs/<feature-slug>.prd.md` — the frozen PRD this run started from
- `./.claude/CLAUDE.md` with the project constitution
- `./.claude/specs/<feature-slug>.md` — spec, traceability, clarifications
- `./.claude/plans/<feature-slug>.md` — technical plan
- `./.claude/tasks/<feature-slug>.md` — actionable tasks

Suggest next steps:
- Commit these files to the repo.
- Send `## Questions for the PRD author` back to whoever wrote the PRD before implementation starts — that's the loop this skill exists to close.
- When starting implementation, invoke whatever skill or subagent you use for coding — the spec, plan, and tasks will be loaded automatically via CLAUDE.md.

## Principles to hold throughout

- **The PRD is the source, not the ceiling.** Everything in the spec that the PRD didn't say is marked `[NEW — not in PRD]` or lives in `## Traceability`. The PM should be able to tell, at a glance, what they decided and what engineering decided.
- **Never silently answer the PM's open questions.** An open question in the PRD stays open through Phase 2. It gets addressed in Phase 3, on the record, not quietly resolved while drafting the spec.
- **Unverified is not true.** A `What's There Today` claim is a claim until Phase 0 or Phase 2 checks it against the repo. Don't build a requirement on top of one that's still unverified.
- **You draft, the human approves.** Every artefact this skill produces should be reviewed. Don't try to close a phase the user hasn't looked at.
- **No code in this skill.** If the user asks for code, redirect: "Let's finish the spec first. Code happens after Phase 5."
- **Be honest about uncertainty.** If a performance threshold is a guess, say so. Don't present guesses as known facts.
