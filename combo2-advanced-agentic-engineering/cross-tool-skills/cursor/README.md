# Cursor — spec-driven reference

Five-phase flow as a Cursor **Rule** (`.mdc`). Cursor 2.4 (January 2026) also supports `SKILL.md` per the agentskills.io standard — the Claude Code `SKILL.md` would work too.

## Layout

```
cursor/
├── AGENTS.md                              # the constitution
└── .cursor/rules/spec-driven.mdc          # the rule
```

## Usage

1. Copy `AGENTS.md` to your repo root.
2. Copy `.cursor/rules/spec-driven.mdc` into your repo.
3. In Cursor: `/spec-driven my-feature` (or `@spec-driven` from the Composer / Agent).

## Rule apply modes

The `.mdc` file uses `alwaysApply: false` (manual invocation only) to mirror Claude Code's `disable-model-invocation: true`. Other modes:

- `alwaysApply: true` — rule attached to every request.
- `alwaysApply: false` + `globs: ["src/api/**"]` — auto-attach when working under those paths.
- `description` only, no globs, no `alwaysApply` — "intelligent" apply driven by the description.

## Alternative — SKILL.md (Cursor 2.4+)

If you'd rather use the agentskills.io schema:

```
cursor/.cursor/skills/spec-driven/SKILL.md
```

The same `SKILL.md` from `../../claude-code-skills/spec-driven/` will work unchanged.
