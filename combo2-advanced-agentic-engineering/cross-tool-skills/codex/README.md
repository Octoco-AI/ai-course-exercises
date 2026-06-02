# Codex CLI — spec-driven reference

Five-phase flow as a Codex CLI **subagent** in TOML. Codex originated the `AGENTS.md` convention.

## Layout

```
codex/
├── AGENTS.md                              # the constitution
└── .codex/agents/spec-driven.toml         # the subagent
```

## Usage

1. Copy `AGENTS.md` to your repo root.
2. Copy `.codex/agents/spec-driven.toml` into your repo (or `~/.codex/agents/` for user-scoped).
3. In Codex CLI: `@spec-driven my-feature`.

## Tuning

- `model`: per-subagent override. Use `gpt-5.5` for planning, switch to `gpt-5.4` or `gpt-5.5-mini` for execution-heavy subagents (Module 7 plan/execute split). 
- `sandbox_mode`: `read-only`, `workspace-write`, or `danger-full-access`. Default `workspace-write` is fine for spec writing.
- `mcp_servers`: list of named MCP servers from your `~/.codex/config.toml` if the skill needs external tool access.
- Global config: `agents.max_threads = 6` (default), `agents.max_depth = 1` (default).
