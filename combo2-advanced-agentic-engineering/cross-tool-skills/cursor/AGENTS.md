# Project constitution (Cursor)

Cursor reads `AGENTS.md` at the start of every session (since 2.4). Keep it under ~200 lines.

## Architecture

- (Stack, frameworks, deployment targets.)
- (Where state lives. Where boundaries are.)

## AI-feature principles

1. Confidence indicators visible to users.
2. Graceful degradation when the model is down.
3. Audit log every AI call.
4. Feedback mechanisms on every AI surface.

## Never-do items

- No medical / legal / financial advice without a licensed reviewer.
- No destructive ops without explicit confirmation.
- No PII to a third-party model without a DPA.

## Delegation norms

- Bucket 1: chores, docs, scoped refactors.
- Bucket 2: features with a spec.
- Bucket 3: architectural / security decisions.
