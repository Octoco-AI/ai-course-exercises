# Project constitution (Codex CLI)

This file is read by Codex CLI at the start of every session. Codex CLI originated the `AGENTS.md` convention; Amp and Cursor have since adopted it.

## Architecture

- (Stack, frameworks, deployment targets.)
- (Where state lives. Where boundaries are.)

## AI-feature principles

1. Confidence indicators visible where AI output drives a user decision.
2. Graceful degradation when the model is unavailable.
3. Audit log every AI call (prompt hash, model + version, latency, cost).
4. Feedback mechanisms on every AI surface.

## Never-do items

- No medical / legal / financial advice without a licensed reviewer.
- No destructive operations without explicit user confirmation.
- No sending PII to a third-party model without a DPA.

## Delegation norms

- Bucket 1 (delegate fully): chores, docs, scoped refactors.
- Bucket 2 (delegate + review): features with a spec.
- Bucket 3 (own yourself): architectural / security decisions.
