# AGENTS.md — OrderBase (C#)

Quick notes for coding agents working in this repo.

- **Stack:** .NET 10, ASP.NET Core Minimal API, raw `Microsoft.Data.Sqlite`. BCL-first.
- **Run:** `dotnet run --project src/LegacyService` (port 5057).
- **Tests:** run `dotnet run --project tests/LegacyService.Tests` — we run the
  test project directly rather than through `dotnet test`; the VSTest bridge
  swallows our console output.
- **Formatting:** run `dotnet format` on any file you touch before
  committing. Format the whole file, not just your diff.
- **Line length:** 120 characters.
- **SQL:** use parameterised queries for anything new.
- **Order ids:** fixed-width, zero-padded. Don't change the width.
- **Don't** add new runtime dependencies or an ORM.
- When in doubt, prefer the smallest change that makes the tests pass.
