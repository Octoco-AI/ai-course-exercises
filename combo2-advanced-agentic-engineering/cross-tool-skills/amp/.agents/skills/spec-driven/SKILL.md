---
description: Walk through the constitution → specify → clarify → plan → tasks flow for a new AI feature. Use when the user asks to "spec out" a feature or starts any AI-touching feature before coding. Pauses between phases for user review.
when_to_use: At the start of any AI-touching feature, before code. Resumes mid-feature if a spec already exists.
disable-model-invocation: true
allowed-tools: Read Write Edit Grep Glob Bash(mkdir:*) Bash(ls:*)
disallowed-tools: Bash(rm:*) Bash(git push:*)
argument-hint: "[feature-name-or-description]"
---

# Spec-driven development (Amp)

This skill walks the five-phase spec-driven flow for a new AI-touching feature. **Pause after each phase. Present the output. Ask the user to approve before moving on.** Do not chain phases.

> Note: this file uses the agentskills.io schema. The same `SKILL.md` runs unmodified under Claude Code (`.claude/skills/spec-driven/`) and Cursor 2.4 (`.cursor/skills/spec-driven/`).

## The feature

$ARGUMENTS

If `$ARGUMENTS` is empty, ask the user: *"What feature are we specifying? One or two sentences."*

## State detection

Before choosing a phase, check what already exists:

1. `AGENTS.md` (or `AGENT.md` / `CLAUDE.md`) with a `## Constitution` heading → Phase 1 done.
2. `./specs/<feature-slug>.md` present → Phase 2 done.
3. `./specs/<feature-slug>.md` has a `## Clarifications` heading → Phase 3 done.
4. `./plans/<feature-slug>.md` present → Phase 4 done.
5. `./tasks/<feature-slug>.md` present → Phase 5 done.

Resume at the first undone phase. Tell the user which phase you're starting.

## Phase 1 — Constitution

Establish project rules every AI feature must follow. Ask about: architecture, AI-feature principles (confidence indicators, graceful degradation, audit logging, feedback mechanisms), never-do items, delegation norms. Draft. Confirm. Write to `AGENTS.md`.

## Phase 2 — Specify

Draft the user story with four extras: performance thresholds, graceful degradation, learning expectations, failure modes. Ask the user for each number; never invent thresholds. Write to `./specs/<feature-slug>.md`. Pause.

## Phase 3 — Clarify

Walk common ambiguity patterns. For each: propose a default with justification, or ask. Append a `## Clarifications` section to the spec. Pause.

## Phase 4 — Plan

Draft a technical plan citing the constitution and spec. Write to `./plans/<feature-slug>.md`. Pause.

## Phase 5 — Tasks

Break the plan into independently-implementable tasks. Write to `./tasks/<feature-slug>.md`. Each task: files, context, validation, lease (files to reserve before editing).

## Principles

- Pause between phases. Approval is the gate.
- Numbers come from the user, not the model.
- Never leave a `TBD` without a named owner and date.
- Commit each phase artefact before moving on.
