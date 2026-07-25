# Changelog

Most recent first. Kept terse; link to PRs for detail.

## 0.14.1 — 2026-04-18

- Fix: N+1 query in `GET /lists/{id}`. Items were loaded one-per-todo; fixed with eager loading. (#412)
- Fix: session cookie's `SameSite` was inconsistent between login and refresh; both now `Strict`. (#414)

## 0.14.0 — 2026-04-10

- Add `position` field to lists. Clients can now reorder. (#401)
- Migration: added `position INTEGER NOT NULL DEFAULT 0` to `lists`. Backward-compatible.

## 0.13.3 — 2026-04-02

- Fix: `PATCH /todos/{id}` accepted unknown fields silently; now returns 422. (#395)

## 0.13.2 — 2026-03-28

- Fix: `invalid_transition` response was 400, should have been 409. Now corrected. **Breaking for strict clients**; we flagged it in the API changelog. (#391)
- Fix: integration test leaking Postgres containers on test failure. (#392)

## 0.13.1 — 2026-03-20

- Fix: honeycomb trace export was dropping spans on shutdown. Added explicit flush. (#388)

## 0.13.0 — 2026-03-12

- **Switch from JWT to session cookies.** This was a deliberate simplification. See `auth.md` for the rationale. The change is invisible to well-behaved mobile clients since they already respect `Set-Cookie`. (#370)
- Removed `/auth/refresh`. Sessions now last 24h on the server; no client-side refresh needed.
- Migration: dropped `users.refresh_token_hash` column.

## 0.12.0 — 2026-02-28

- Add soft-delete to todos. `DELETE /todos/{id}` now sets `deleted_at` instead of removing the row. Hard deletes run via `ops/gc.py` in a nightly Fly machine. (#355)
- Migration: added `todos.deleted_at TIMESTAMP WITH TIME ZONE NULL`.

## 0.11.0 — 2026-02-10

- Add archived status to todos. Status transitions are now enforced: `open → completed → archived`, one-way. (#340)
- Migration: `todos.status` widened from `VARCHAR(16)` to enum-backed; data migrated in place.

## 0.10.0 — 2026-01-25

- First open-source release. Preceded by 6 months of internal development.

## Pre-0.10

Not documented here. Commit history starts clean at 0.10.
