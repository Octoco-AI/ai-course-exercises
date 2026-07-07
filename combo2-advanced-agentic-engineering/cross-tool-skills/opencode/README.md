# OpenCode — spec-driven reference

Five-phase flow as an OpenCode **primary agent** (markdown + YAML frontmatter). OpenCode is OSS and provider-agnostic — bring your own model.

## Layout

```
opencode/
├── opencode.json                          # project config + constitution
└── .opencode/agents/spec-driven.md        # the agent
```

## Usage

1. Copy `opencode.json` to your repo root and customise the constitution block.
2. Copy `.opencode/agents/spec-driven.md` into your repo (or `~/.config/opencode/agents/` for user-scoped).
3. In OpenCode: `@spec-driven my-feature`.

## Notes

- `mode: primary` means this agent is invokable as the top-level driver. Use `mode: subagent` if you want it usable only via `@spec-driven` from another agent.
- `model: anthropic/claude-sonnet-5` — change provider/model freely. OpenCode supports 75+ providers via Models.dev (Anthropic, OpenAI, Google, Mistral, local via Ollama, etc.).
- `allow` / `ask` / `deny` — the three-tier permission model. `deny` overrides `ask` overrides `allow`. Useful for catastrophic actions (`Bash(rm:*)`, `Bash(git push:*)`).
- If you want full `SKILL.md` (agentskills.io) compat, install the community plugin `opencode-agent-skills`.
