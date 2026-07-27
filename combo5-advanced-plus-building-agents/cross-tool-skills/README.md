# Cross-tool spec-driven skill — reference implementations

Five minimal `spec-driven` skill implementations, one per agent harness, for use as reference alongside the Claude Code lightweight path taught in Module 3 (`m3-specs-with-teeth-full`).

| Tool | Subdirectory | Constitution file | Skill / agent file | Invocation |
|---|---|---|---|---|
| Amp | `amp/` | `AGENTS.md` (or `AGENT.md` / `CLAUDE.md`) | `.agents/skills/spec-driven/SKILL.md` | `/spec-driven <feature>` |
| Codex CLI | `codex/` | `AGENTS.md` | `.codex/agents/spec-driven.toml` | `@spec-driven` |
| Cursor | `cursor/` | `AGENTS.md` | `.cursor/rules/spec-driven.mdc` (or `SKILL.md` since 2.4) | `/spec-driven <feature>` |
| Gemini CLI | `gemini-cli/` | `GEMINI.md` | `.gemini/agents/spec-driven.md` | `@spec-driven` |
| OpenCode | `opencode/` | `opencode.json` rules | `.opencode/agents/spec-driven.md` | `@spec-driven` |

Each subdirectory contains the bare minimum to run the five-phase flow on a sample feature. None of these are intended as production-quality skills — they're reference patterns so the discipline is visible across harnesses.

The full Claude Code lightweight reference (with `templates/`, state detection, pause-for-approval logic) is at `../claude-code-skills/spec-driven/`. The agentskills.io standard means the Claude Code `SKILL.md` runs unmodified under Amp and Cursor 2.4.

## When to use these

- You picked a tool other than Claude Code or SpecKit and want a skeleton to start from.
- You want to compare how the same discipline expresses across harnesses.
- You're authoring a workshop talk and need a concrete demo per tool.

Not for use as: a complete workshop exercise on the day (Combo 2 M3 hands-on is Claude Code + SpecKit only).
