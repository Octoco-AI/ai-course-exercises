# Codex CLI Skills — Combo 5 reference

Workshop-authored Codex CLI skills for Combo 5 Module 3b (*Specs with teeth — lightweight path*). Attendees install these during the module, then customise for their own project.

This is the Codex sibling of `../claude-code-skills/`. Same five-phase discipline, same templates — the differences are where the constitution lives (`AGENTS.md`, not `CLAUDE.md`), where the skill installs (`~/.codex/skills/`, not `~/.claude/skills/`), and how you invoke it.

## Contents

- **`spec-driven/SKILL.md`** — the main skill. Walks through constitution → specify → clarify → plan → tasks. Pauses between phases for review.
- **`spec-driven/templates/`** — reference templates loaded on demand by the skill:
  - `constitution-template.md` — what project rules look like.
  - `spec-template.md` — the four-extras pattern (thresholds / degradation / learning / failure modes).
  - `clarify-checklist.md` — 25 ambiguity patterns to surface before planning.
  - `plan-template.md` — technical-plan structure.
  - `tasks-template.md` — how to break a plan into mergeable tasks.
- **`AGENTS.md.example`** — example project constitution (output of Phase 1).
- **`agents/spec-driven.toml`** — optional sub-agent flavour of the same flow, for teams that want a declaratively pinned model / effort / sandbox. Not needed for the exercise.

---

## Installation

Two scopes to choose from. Pick one based on how much of your team should have it:

### Personal (just you, all projects)

```bash
mkdir -p ~/.codex/skills/spec-driven
cp -r spec-driven/* ~/.codex/skills/spec-driven/
```

### Project (your team, this project only)

```bash
cd /path/to/your/project
mkdir -p .codex/skills/spec-driven
cp -r /path/to/workshop/examples/codex-skills/spec-driven/* .codex/skills/spec-driven/
git add .codex/skills/spec-driven
git commit -m "Add spec-driven skill"
```

Anyone on the team with Codex CLI gets the skill when they clone the repo.

### Confirm it landed

Start a Codex session and run `/skills`. `spec-driven` should be in the picker. If it isn't, the usual cause is a missing or malformed `name` in the frontmatter — see *Common failures* in `FACILITATOR.md`.

---

## Running the skill

From any Codex CLI session in a project:

```
/skills                → pick spec-driven
Personalised video recommendations for ADHD-parent training
```

Three ways in:

- `/skills` → pick `spec-driven` from the menu. **The one to use during the exercise** — it works on every build.
- Describe the task in plain language ("let's spec out the recommendations feature") — Codex matches on the skill's `description` and pulls it in.
- `$spec-driven <feature>` — a shorthand recent builds accept. If it doesn't resolve on your version, fall back to `/skills`; nothing else changes.

The skill will:

1. Check your project for existing constitution / spec / plan / tasks files and pick up where you left off.
2. Walk you through the current phase, pausing at the end to ask for your approval.
3. Write its outputs to `./AGENTS.md`, `./specs/`, `./plans/`, `./tasks/`.

At any point you can say *"stop"* or *"let's come back to this later"* — your work so far is on disk.

---

## Differences from the Claude Code version

Same methodology, four mechanical differences. Worth knowing if your team runs both tools.

| | Claude Code | Codex CLI |
|---|---|---|
| **Skill path** | `~/.claude/skills/<name>/` or `.claude/skills/<name>/` | `~/.codex/skills/<name>/` or `.codex/skills/<name>/` |
| **Invocation** | `/spec-driven <feature>` slash command | `/skills` picker (some builds also accept `$spec-driven <feature>`) |
| **Constitution** | `CLAUDE.md` | `AGENTS.md` |
| **Artefacts** | `./.claude/specs/`, `./.claude/plans/`, `./.claude/tasks/` | `./specs/`, `./plans/`, `./tasks/` |

The Claude Code version's frontmatter also carries `disable-model-invocation`, `allowed-tools` and `argument-hint`. Codex ignores those keys — it has no *per-skill* tool allowlist. Scope in Codex comes from three places instead:

- `sandbox_mode` and `approval_policy` in `config.toml` (session level), or the per-agent `sandbox_mode` shown in `agents/spec-driven.toml`.
- A `pre_tool_use` hook in `.codex/hooks.json` for anything finer — it fires before every tool call and blocks on exit `2` with a reason on stderr, the same mechanism as Claude Code's `PreToolUse`.

So the enforcement is equivalent; what differs is that the rule can't live *inside* the skill file. That trade-off comes up again in the security-and-governance module, where the question turns out to be less "which is stronger" than "will the next person editing this agent see the rule?"

Because both tools read plain `SKILL.md` files, the skill body itself is nearly identical between the two directories — diff them if you want to see exactly what changed.

---

## When to use this vs the SpecKit path

Two valid approaches for spec-driven development. Pick based on your team's stack:

| | Codex CLI skill (this) | SpecKit |
|---|---|---|
| **Extra install** | None — just Codex CLI | `uv tool install specify-cli` |
| **Works with** | Codex CLI (and, unchanged, any harness that reads `SKILL.md`) | 30+ agents (Copilot, Cursor, Gemini CLI, etc.) |
| **Customisation** | Edit `SKILL.md` and templates in your repo | Fork / create a preset |
| **Best for** | Teams mostly on Codex | Mixed-tool teams; multi-IDE shops |

Both implement the same conceptual flow. The lightweight skill version is what Combo 5 Module 3b live-creates; SpecKit is shown in M10c.

---

## Customising

Edit `SKILL.md` to add or remove phases. The templates in `templates/` are referenced from the skill body — tweak them to match your project's conventions. For example:

- Swap the four-extras pattern for your org's user-story template.
- Add a new phase (e.g. "legal review" between plan and tasks).
- Retarget the artefact paths if your repo already has a `docs/specs/` convention.

After editing, restart the Codex session — skills are read at startup.

---

## What this skill is NOT

- **Not SpecKit.** See above. Different tool, same methodology.
- **Not a code generator.** The skill deliberately does not write implementation code — Phase 5 outputs tasks, and a separate skill (or your manual review) drives implementation.
- **Not a replacement for PM.** The skill helps structure thinking; it doesn't know your user research. The spec output should be reviewed by a human who knows the users.
- **Not a silver bullet for non-determinism.** Writing a threshold in a spec doesn't make the AI meet it. Evals (M11 / M12) do.

---

## Splitting into per-phase skills (advanced)

If you prefer invoking each phase separately (`$spec-specify` then `$spec-plan`), split `spec-driven/SKILL.md` into five smaller skills:

- `~/.codex/skills/spec-constitution/SKILL.md` — Phase 1 only.
- `~/.codex/skills/spec-specify/SKILL.md` — Phase 2 only.
- `~/.codex/skills/spec-clarify/SKILL.md` — Phase 3 only.
- `~/.codex/skills/spec-plan/SKILL.md` — Phase 4 only.
- `~/.codex/skills/spec-tasks/SKILL.md` — Phase 5 only.

Each needs a frontmatter `name` matching the intended invocation. Copy the relevant phase section from the main `SKILL.md` into each; the templates in `templates/` are referenced the same way.

**Trade-off**: more skills, each smaller and more focused. Lets the team decide which phases are valuable on a given day.

Codex ships `$skill-creator` for scaffolding a new skill interactively and `$skill-installer` for install / update / removal — both useful if you go down this road.
