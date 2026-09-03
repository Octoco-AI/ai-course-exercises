# Claude Code Skills — Combo 2 reference

Workshop-authored Claude Code skills for Combo 2 Module 3b (*Specs with teeth — lightweight path*). Attendees install these during the module, then customise for their own project.

## Contents

- **`spec-driven/SKILL.md`** — the main skill. Walks through constitution → specify → clarify → plan → tasks. Pauses between phases for review. Starts from nothing.
- **`spec-driven/templates/`** — reference templates loaded on demand by the skill:
  - `constitution-template.md` — what project rules look like.
  - `spec-template.md` — the four-extras pattern (thresholds / degradation / learning / failure modes).
  - `clarify-checklist.md` — 25 ambiguity patterns to surface before planning.
  - `plan-template.md` — technical-plan structure.
  - `tasks-template.md` — how to break a plan into mergeable tasks.
- **`CLAUDE.md.example`** — example project constitution (output of Phase 1).
- **`spec-from-prd/SKILL.md`** — sibling skill. Starts from a product PRD (typically one drafted with Combo 7's `write-lean-prd` skill) instead of a cold start: intake → constitution → specify → clarify → plan → tasks. See *"`spec-driven` vs `spec-from-prd`"* below for when to reach for which.
- **`spec-from-prd/templates/`** — the same five templates as `spec-driven/` (`plan-template.md` is an unmodified copy; `constitution-template.md`, `spec-template.md`, `clarify-checklist.md` and `tasks-template.md` are variants with PRD-tracing additions — diff them if you want to see exactly what changed), plus two new ones:
  - `prd-intake-checklist.md` — how to read a lean PRD section by section: what carries forward, what needs verifying against the repo, what it structurally cannot tell you.
  - `prd-to-spec-map.md` — where each PRD section lands in the spec, worked through the sample PRD below.
- **`example-prd.md`** — a sample PRD in `write-lean-prd`'s exact output shape ("AI-Assisted PR Review Triage"), for running `spec-from-prd` without a real PRD to hand. It has two requirements that fail the durability test, a `What's There Today` claim the repo can contradict, and an open question `spec-from-prd` must carry forward rather than resolve — run the skill on it and see whether it catches all three.

---

## Installation

Three scopes to choose from. Pick one based on how much of your team should have it:

### Personal (just you, all projects)

```bash
mkdir -p ~/.claude/skills/spec-driven
cp -r spec-driven/* ~/.claude/skills/spec-driven/
```

Invoke in any Claude Code session: `/spec-driven "<feature name>"`.

### Project (your team, this project only)

```bash
cd /path/to/your/project
mkdir -p .claude/skills/spec-driven
cp -r /path/to/workshop/examples/claude-code-skills/spec-driven/* .claude/skills/spec-driven/
git add .claude/skills/spec-driven
git commit -m "Add spec-driven skill"
```

Anyone on the team with Claude Code will get the skill when they clone the repo.

### Organisation-wide

See the Claude Code enterprise docs for managed-settings deployment. The skill copy is the same; the path is OS-specific.

### Also installing `spec-from-prd`

Same three scopes, same commands, `spec-from-prd` in place of `spec-driven`:

```bash
mkdir -p ~/.claude/skills/spec-from-prd
cp -r spec-from-prd/* ~/.claude/skills/spec-from-prd/
```

Invoke: `/spec-from-prd "<path-to-prd>"` (or just `/spec-from-prd` and point it at the PRD when asked).

---

## Running the skill

From any Claude Code session in a project:

```
/spec-driven "Personalised video recommendations for ADHD-parent training"
```

The skill will:

1. Check your project for existing constitution / spec / plan / tasks files and pick up where you left off.
2. Walk you through the current phase, pausing at the end to ask for your approval.
3. Write its outputs into `./.claude/specs/`, `./.claude/plans/`, `./.claude/tasks/`.

At any point you can say *"stop"* or *"let's come back to this later"* — your work so far is on disk.

---

## `spec-driven` vs `spec-from-prd`

Same five downstream phases, same artefact paths, same state-detection files — a feature
started with one resumes cleanly with the other. The only question is what you start from:

| | `spec-driven` | `spec-from-prd` |
|---|---|---|
| **Starting point** | Nothing — a feature name or a one-line description | A PRD (typically Combo 7's `write-lean-prd` output), plus any designs or notes |
| **Phase 0** | None — goes straight to constitution | Intake: freeze the PRD, read the repo, run `prd-intake-checklist.md` |
| **Constitution** | Interviews you from scratch | Drafts from the PRD's `Out of scope` and `Goals` first, asks only for what a PRD can't supply (delegation norms) |
| **Specify** | Drafts the four-extras story with you from nothing | Carries the PRD's requirements and scenarios forward, restating any that leak implementation; adds a `## Traceability` table and `## Questions for the PRD author` |
| **Clarify** | Walks the 25-item checklist | Starts with the PRD's own `## Open Questions`, then walks the 25-item checklist plus a PRD-gap group |
| **Use when** | You're specifying without a PM handoff | A PM (or Combo 7) already handed you a lean PRD |

Try `spec-from-prd` on `example-prd.md` before you try it on a real PRD — it's built to have
a few things worth catching.

---

## When to use this vs the SpecKit path

Two valid approaches for spec-driven development. Pick based on your team's stack:

| | Claude Code skill (this) | SpecKit |
|---|---|---|
| **Extra install** | None — just Claude Code | `uv tool install specify-cli` |
| **Works with** | Claude Code only | 30+ agents (Copilot, Cursor, Gemini CLI, etc.) |
| **Customisation** | Edit `SKILL.md` and templates in your repo | Fork / create a preset |
| **Best for** | Teams mostly on Claude Code | Mixed-tool teams; multi-IDE shops |

Both implement the same conceptual flow. The Claude Code skill version is what Combo 2 Module 3b live-creates; SpecKit is shown in M10c.

---

## Customising

Edit `SKILL.md` to add or remove phases. The templates in `templates/` are referenced from the skill body — tweak them to match your project's conventions. For example:

- Swap the four-extras pattern for your org's user-story template.
- Add a new phase (e.g. "legal review" between plan and tasks).
- Restrict `allowed-tools` if you want tighter permissions.

After editing, Claude Code picks up changes on the next session (the skill directory is watched in real time per the skills docs).

`spec-from-prd/templates/plan-template.md` and `constitution-template.md` are near-duplicates
of `spec-driven`'s — deliberately. Each skill directory is meant to be self-contained once
installed on its own (personal-scope install copies exactly one directory), so a shared
template loaded via a cross-skill relative path would silently break the moment someone
installs `spec-from-prd` without `spec-driven` alongside it. If you customise one, check
whether the other should change too.

---

## What this skill is NOT

- **Not SpecKit.** See above. Different tool, same methodology.
- **Not a code generator.** The skill deliberately does not write implementation code — Phase 5 outputs tasks, and a separate skill (or your manual review) drives implementation.
- **Not a replacement for PM.** The skill helps structure thinking; it doesn't know your user research. The spec output should be reviewed by a human who knows the users.
- **Not a silver bullet for non-determinism.** Writing a threshold in a spec doesn't make the AI meet it. Evals (M11 / M12) do.
- **`spec-from-prd` is not `write-lean-prd`.** It consumes a PRD; it doesn't write one. If you need to draft the PRD itself, that's Combo 7's `write-lean-prd` skill — different audience, different artefact, different tool (it runs in claude.ai chat, not Claude Code).

---

## Splitting into per-phase skills (advanced)

If you prefer invoking each phase separately (e.g. `/spec:specify` then `/spec:plan`), split `spec-driven/SKILL.md` into five smaller skills:

- `.claude/skills/spec-constitution/SKILL.md` — Phase 1 only.
- `.claude/skills/spec-specify/SKILL.md` — Phase 2 only.
- `.claude/skills/spec-clarify/SKILL.md` — Phase 3 only.
- `.claude/skills/spec-plan/SKILL.md` — Phase 4 only.
- `.claude/skills/spec-tasks/SKILL.md` — Phase 5 only.

Each has a frontmatter `name` matching the intended slash command. You can copy the relevant phase section from the main SKILL.md into each. The templates in `templates/` are referenced the same way.

**Trade-off**: more skills, each smaller and more focused. Lets the team decide which phases are valuable on a given day.
