# Codex CLI — spec-driven reference

Five-phase flow as a Codex CLI **sub-agent** in TOML. Codex originated the `AGENTS.md` convention.

> **Not the default path any more.** Codex reads `SKILL.md` natively, so the primary Codex reference is `../../codex-skills/` — the same file the Claude Code path uses, with retargeted artefact paths. Keep this TOML flavour for when you want the model, reasoning effort and sandbox pinned declaratively in a committed file.

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

- `model`: per-sub-agent override. Frontier tier for planning, the fast/affordable tier for execution-heavy sub-agents (Module 14 plan/execute split). Run `codex debug models` for the current ladder — at time of writing `gpt-5.6-sol` → `gpt-5.6-terra` → `gpt-5.6-luna`, with the `gpt-5.4` family hidden. Omit the key to inherit the parent session's model.
- `model_reasoning_effort`: `low` / `medium` / `high` / `xhigh`, plus `max` / `ultra` on the 5.6 family. The thinking dial — up on planners, down on executors. Independent of `model`, which makes it the more durable of the two levers.
- `sandbox_mode`: `read-only`, `workspace-write`, or `danger-full-access`. Default `workspace-write` is fine for spec writing.
- `mcp_servers`: list of named MCP servers from your `~/.codex/config.toml` if the skill needs external tool access.
- Global config: sub-agent concurrency and nesting depth are capped in `~/.codex/config.toml`. Current builds use `max_concurrent_threads_per_session` and `max_depth`; the key names have been renamed before, so check the config reference for your version rather than trusting this line.
