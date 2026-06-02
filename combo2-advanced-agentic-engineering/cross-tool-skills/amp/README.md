# Amp (ampcode) — spec-driven reference

Closest 1:1 to the Claude Code lightweight path. Amp follows the agentskills.io standard, so the same `SKILL.md` runs unmodified under Claude Code and Amp.

## Layout

```
amp/
├── AGENTS.md                                  # the constitution
├── .agents/skills/spec-driven/SKILL.md        # the skill
└── (specs/, plans/, tasks/ created on use)
```

## Usage

1. Copy `AGENTS.md` to your repo root (Amp also reads `AGENT.md` and `CLAUDE.md`).
2. Copy `.agents/skills/spec-driven/` into your repo (or `~/.agents/skills/` for user-scoped).
3. In Amp: `/spec-driven my-feature` to start Phase 1, or `/spec-driven` with no args to be asked for one.

## Notes

- Amp's `smart` mode (Opus 4.7) handles the spec drafting well. `deep` is overkill here.
- `disallowed-tools` is honoured by Amp's permission system as of v0.x.
- The `SKILL.md` body is intentionally minimal — the full reference at `../../claude-code-skills/spec-driven/` has templates and richer state-detection prose.
