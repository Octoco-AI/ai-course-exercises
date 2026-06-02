# Gemini CLI — spec-driven reference

Five-phase flow as a Gemini CLI **subagent** (markdown + YAML frontmatter). Gemini CLI shipped subagents in April 2026.

## Layout

```
gemini-cli/
├── GEMINI.md                              # the constitution
└── .gemini/agents/spec-driven.md          # the subagent
```

## Usage

1. Copy `GEMINI.md` to your repo root.
2. Copy `.gemini/agents/spec-driven.md` into your repo (or `~/.gemini/agents/` for user-scoped).
3. In Gemini CLI: `@spec-driven my-feature`.

## Notes

- `model: gemini-2.5-pro` for the planning phases; switch to `gemini-2.5-flash` if you want cheaper drafting and you'll review carefully.
- Gemini's free tier (60 req/min, 1k/day) covers workshop-scale work end-to-end.
- 1M-token context means large codebases fit without chunking — useful for Phase 4 (Plan) when the agent has to reason over many files.
- `tools` is the subagent allowlist; matches the same principle-of-least-privilege pattern Claude Code uses.
