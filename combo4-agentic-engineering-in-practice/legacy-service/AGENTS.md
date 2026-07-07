# AGENTS.md — OrderBase

Quick notes for coding agents working in this repo.

- **Stack:** Python 3.10+, Flask, raw `sqlite3`. Stdlib-first.
- **Run:** `python -m legacy_service.app` (port 5057).
- **Tests:** run `python -m unittest discover -s tests -v`. Keep them fast.
- **Formatting:** run `black` (line length 88) on any file you touch before
  committing. Format the whole file, not just your diff.
- **Line length:** 88 characters.
- **SQL:** use parameterised queries for anything new.
- **Order ids:** fixed-width, zero-padded. Don't change the width.
- **Don't** add new runtime dependencies or an ORM.
- When in doubt, prefer the smallest change that makes the tests pass.
