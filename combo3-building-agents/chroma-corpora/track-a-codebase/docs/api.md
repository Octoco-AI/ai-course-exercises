# HTTP API

All routes are JSON-in, JSON-out. Authentication is session-cookie based. Unauthenticated routes are explicitly marked `(public)`.

## Auth

### `POST /auth/login` (public)

Body: `{"email": "user@example.com", "password": "..."}`

On success: 200 with `{"user": {...}}`, `Set-Cookie: session=<token>; HttpOnly; Secure; SameSite=Strict`.

On failure: 401 with `{"error": "invalid_credentials"}`. Same status for unknown email and wrong password — we don't leak which.

### `POST /auth/logout`

Revokes the current session. Always returns 204.

### `GET /auth/me`

Returns the currently-authenticated user, or 401.

## Lists

### `GET /lists`

Returns all lists belonging to the current user. Sorted by `position` ascending. Pagination is not supported; a user who has more than 100 lists is likely a bug, not a feature.

### `POST /lists`

Body: `{"name": "Groceries", "position": 3}` (position optional; defaults to the max + 1).

Returns 201 with the created list.

### `GET /lists/{id}`

Returns a list, its items, and basic stats (`{"open_count", "completed_count", "archived_count"}`). 404 if the list doesn't exist or doesn't belong to the current user — same status for both to avoid leaking existence.

### `PATCH /lists/{id}`

Partial update. Fields: `name`, `position`. Other fields are rejected (400).

### `POST /lists/{id}/archive`

Archives the list. Does not affect items. Archived lists don't appear in `GET /lists` by default. Pass `?include_archived=true` to see them. You cannot archive a list that's already archived (409).

## Todos

### `GET /lists/{list_id}/todos`

Query parameters:
- `status`: `open` | `completed` | `archived`. Default: `open`.
- `limit`: default 50, max 200.
- `cursor`: opaque pagination cursor from the previous response.

Returns: `{"todos": [...], "next_cursor": "..." | null}`.

### `POST /lists/{list_id}/todos`

Body: `{"title": "Buy milk", "description"?: "...", "due_date"?: "ISO-8601"}`.

### `PATCH /todos/{id}`

Partial update. Fields: `title`, `description`, `due_date`, `status`. Status transitions are enforced server-side: `open → completed → archived` only. Going backwards returns 409.

### `DELETE /todos/{id}`

Soft-delete. The todo is hidden from all read endpoints unless `?include_deleted=true` is passed. Hard deletes happen via a nightly batch job in `ops/gc.py`.

## Errors

All error responses have shape `{"error": "<slug>", "detail": "<human-readable>", "request_id": "<id>"}`. Error slugs are stable and documented; the detail string is for humans and can change.

Common slugs:
- `invalid_credentials`
- `not_authenticated`
- `not_authorized`
- `not_found`
- `invalid_transition`
- `validation_failed`
- `internal_error`
