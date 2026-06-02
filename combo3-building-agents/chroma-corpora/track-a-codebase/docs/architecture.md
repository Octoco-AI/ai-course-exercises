# Architecture

## Layers

Requests flow through four layers, top to bottom:

```
HTTP (FastAPI)  →  api/
Business logic  →  services/
Data access     →  storage/
Database        →  Postgres
```

Each layer only talks to the layer directly below. `services/` never imports `sqlalchemy`. `api/` never queries the database directly. Violations of this rule are caught in code review; the convention exists because it keeps services pure and unit-testable.

## The storage layer

`src/todomagic/storage/` holds the repository pattern. One repository per aggregate root: `TodoRepository`, `ListRepository`, `UserRepository`. Each repository exposes a small set of methods with named keyword arguments (`get_by_id`, `list_by_user`, `save`, `delete`). Queries live inside the repository; the rest of the code does not see SQL.

Repositories accept a `Session` in their constructor (SQLAlchemy session, not HTTP session). FastAPI's dependency-injection system provides a request-scoped session. Tests inject a session bound to an in-memory SQLite for speed, or to a throwaway Postgres database for integration coverage.

## The services layer

`src/todomagic/services/` holds business logic. Services accept dependencies through their constructor — typically repositories and the session-token backend. Services never import from `api/` or `sqlalchemy`.

Each service method is a single unit of behaviour. `CompleteTodoService.execute(todo_id, by_user_id)` is typical: read, check, write. Services raise domain exceptions (`InvalidTransition`, `NotAuthorized`) which the API layer converts to HTTP status codes.

## Auth

Sessions are opaque tokens stored in Redis with a 24-hour TTL. On login, the API handler calls `AuthService.create_session(user_id)` which writes the token to Redis and sets it as an HttpOnly cookie. On each subsequent request, FastAPI's `get_current_user` dependency reads the cookie, looks up Redis, returns the `User` or raises `401`.

No JWT. No refresh tokens. We accepted the trade-off: every authenticated request hits Redis. Cost is ~1ms and we don't log out stale tokens on the client — the server decides.

## Data model highlights

The schema is small. Three tables: `users`, `lists`, `todos`. Relationships:

- User has many Lists.
- List has many Todos.
- Todo belongs to exactly one List.

Indexes worth knowing about:
- `todos (list_id, status, due_date)` — supports the "list open items in this list, soonest first" query, which is the single most common read.
- `lists (user_id)` — supports the landing page.
- `users (email)` unique — supports login.

Soft-delete: a `deleted_at` column on Todo. The query layer filters out `deleted_at IS NOT NULL` by default; pass `include_deleted=True` to see them. Lists cannot be deleted; they archive instead.

## Observability

- Structured logs via `structlog` to stdout. Fly ingests to Loki.
- Request tracing via `opentelemetry` to Honeycomb.
- Metrics: `prometheus-fastapi-instrumentator`; scraped by Fly's managed Prometheus.

Logs are correlated by `request_id` (set by middleware from `X-Request-ID` if provided, else a new UUID). Traces carry the same `request_id` as a span attribute.
