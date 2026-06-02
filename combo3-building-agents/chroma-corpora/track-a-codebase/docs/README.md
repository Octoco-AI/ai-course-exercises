# TodoMagic

A small todo-list microservice used as the fictional codebase for Track A of Combo 3's running artefact. The agent in M4 answers questions about this code using a Chroma-indexed corpus of the documents under this directory.

## What TodoMagic does

TodoMagic is a HTTP service that lets users create, update, complete, and delete todo items. Each item belongs to exactly one list; lists belong to a user. Items have a title, optional description, optional due date, and a status (`open` / `completed` / `archived`).

The service is intended as a simple backend for a personal-productivity mobile app. It is not a full project-management tool — there are no tags, no collaborators, no subtasks, no attachments.

## Stack

- **Python 3.12+** with FastAPI for the HTTP layer.
- **Postgres** as the data store, accessed via SQLAlchemy.
- **Redis** for session tokens (session-based auth; not JWT).
- **Deployed** to Fly.io in a single-region configuration.

## Repository layout

```
todomagic/
├── src/todomagic/
│   ├── api/          # FastAPI route handlers
│   ├── models/       # SQLAlchemy models
│   ├── services/     # Business logic (no HTTP, no DB — pure)
│   ├── storage/      # Repository layer; only module that imports SQLAlchemy
│   └── auth/         # Session handling
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── ops/              # Fly config, migration scripts
```

## Design principles we hold to

- **Services are pure.** No HTTP, no DB, no I/O. All reads and writes go through the storage layer. This lets unit tests of services run in microseconds without a DB.
- **One SQL per request in the happy path.** We avoid N+1 selects by eagerly loading relationships where needed. Integration tests assert query count.
- **Sessions live in Redis, not the DB.** Sessions are ephemeral; keeping them out of the main DB means we can truncate on Redis restart without touching durable data.
- **Status transitions are explicit.** A todo's status moves `open → completed → archived`. You cannot go backwards. The service layer enforces this and raises `InvalidTransition` on violation.

## What's NOT in this codebase

- No notifications, email, or push.
- No team / collaboration features.
- No billing.
- No rate limiting (we rely on Fly's upstream).
- No AI-powered anything. This is deliberately boring.
