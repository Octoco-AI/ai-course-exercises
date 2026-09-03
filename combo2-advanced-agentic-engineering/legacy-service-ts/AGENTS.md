# AGENTS.md — OrderBase (TypeScript)

Quick notes for coding agents working in this repo.

- **Stack:** Node 22+, Express, the built-in `node:sqlite`. Runtime-first.
- **Run:** `npm start` (port 5057).
- **Tests:** run `node --test tests/` — we use the built-in Node test
  runner. Keep them fast.
- **Formatting:** run `prettier --write` on any file you touch before
  committing. Format the whole file, not just your diff.
- **Line length:** 80 characters.
- **SQL:** use parameterised queries for anything new.
- **Order ids:** fixed-width, zero-padded. Don't change the width.
- **Don't** add new runtime dependencies or a query builder.
- When in doubt, prefer the smallest change that makes the tests pass.
