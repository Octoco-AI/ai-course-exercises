# AGENTS.md — OrderBase (Java)

Quick notes for coding agents working in this repo.

- **Stack:** Java 21, Spring Boot only for HTTP routing, raw `sqlite-jdbc`.
  JDK-first.
- **Run:** `./mvnw spring-boot:run` (port 5057).
- **Tests:** run `./mvnw -q test -Dtest=LegacyServiceSmokeTests` — Surefire's
  full-module output buries the assertion you actually care about under
  Spring Boot's context-startup noise, so scope the run to the smoke test
  class by name.
- **Line length:** 120 characters.
- **SQL:** use parameterised queries for anything new.
- **Order ids:** fixed-width, zero-padded. Don't change the width.
- **Don't** add new runtime dependencies or an ORM.
- When in doubt, prefer the smallest change that makes the tests pass.
