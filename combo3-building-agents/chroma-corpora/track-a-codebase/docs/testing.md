# Testing

Three levels of tests, each with its own pytest directory and CI job.

## Unit tests (`tests/unit/`)

Pure-function or pure-service tests. No database, no HTTP, no Redis. Services are tested with hand-built fake repositories that implement the same interface as the real ones (duck-typed; no ABC).

Run: `pytest tests/unit/`. Should complete in under 5 seconds.

Example targets:
- Status-transition logic in `services/complete_todo.py`.
- Sort ordering in `services/list_todos.py`.
- Input validation in the Pydantic request schemas.

## Integration tests (`tests/integration/`)

Services + repositories + a real Postgres. No HTTP layer. A throwaway database is spun up via `testcontainers` at session scope; each test gets a transaction that's rolled back.

Run: `pytest tests/integration/`. Typically 15–30 seconds including DB startup.

Example targets:
- Repository queries: do they return the right rows?
- Transaction boundaries: does `CompleteTodoService` roll back on failure?
- Query count assertions: does the "list items in a list" query really use one SELECT?

## End-to-end tests (`tests/e2e/`)

Full stack: FastAPI via `httpx.AsyncClient`, real Postgres, real Redis (also testcontainers). Each test creates its own user and operates against real cookies.

Run: `pytest tests/e2e/`. 30–60 seconds.

Example targets:
- Full login → create-list → add-todo → complete → archive happy path.
- 401 vs 404 leakage — does the API correctly obscure whether resources exist?
- Session expiry: does a token stop working after 24 hours? (We manipulate Redis TTL directly.)

## Coverage

We track coverage but don't gate on a number. Current CI reports:
- Unit: ~90%
- Integration: covers repository methods
- E2E: covers every happy-path route

A drop of more than 5% blocks CI. The rationale is the threshold catches someone deleting a test without replacing it — we don't chase a coverage number.

## What's NOT tested here

- **Performance / load.** We use k6 scripts in `ops/load/` run on-demand; no CI.
- **Fly deploys.** Smoke-tested manually after each release.
- **Third-party API contracts.** None (we have no external dependencies beyond Postgres + Redis).
