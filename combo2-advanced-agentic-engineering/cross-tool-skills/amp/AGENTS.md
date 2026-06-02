# Project constitution (Amp / agentskills.io)

This file is read by Amp at the start of every session. Amp also reads `AGENT.md` and `CLAUDE.md` as fallbacks. Keep it under ~200 lines.

## Architecture

- (Stack, frameworks, deployment targets.)
- (Where state lives. Where boundaries are.)

## AI-feature principles

1. **Confidence indicators are user-visible** where the AI output drives a decision.
2. **Graceful degradation** when the model is unavailable: fall back to (rules / cached responses / a human-in-the-loop queue).
3. **Audit log** every AI call with prompt hash, model + version, latency, cost, outcome.
4. **Feedback mechanisms** on every AI surface — at least thumbs up/down + free text.

## Never-do items

- No medical/legal/financial advice claims without a licensed reviewer in the loop.
- No destructive operations without explicit user confirmation.
- No sending PII to a third-party model without a DPA on file.

## Delegation norms

- Bucket 1 (delegate fully): tickets matching `chore/`, `docs/`, scoped refactors.
- Bucket 2 (delegate + review): features with a spec.
- Bucket 3 (own yourself): architectural decisions, security-sensitive code.

(Customise the above to your team before committing.)
