# OrderBase (C#) — Engineering Guidelines & Working Notes

## Who we are

We are the OrderBase team. We own the order-tracking service that has been in
production since 2018. We are a small, senior, pragmatic team and we care
deeply about reliability, correctness, clean code, and doing right by the
downstream consumers (the WMS, the fulfilment sync, the reconcile cron, and
the finance ledger). We value collaboration, honest communication, and
shipping code we are not embarrassed by. We are always trying to improve, and
we believe the codebase should get a little better every time someone touches
it.

## How we work

- We use pull requests for all changes. No direct commits to main.
- We write tests. Tests are documentation as much as they are verification.
- We value code review and we review kindly.
- We keep commits small and focused.
- We prefer simple code over clever code.
- We refactor opportunistically when we see something that can be improved.
- We write clean, readable, self-documenting code.
- We leave the campsite cleaner than we found it.

## Coding conventions

- C# only in this repo. Target .NET 10.
- Use 4-space indentation. No tabs, ever.
- Keep lines under 100 characters.
- Prefer `$"..."` interpolation for new code, but note that most of this repo
  uses `string.Format` and `+` concatenation — match the surrounding style
  when editing.
- Use descriptive names. `orderId`, not `oid` or `x`.
- Write clean code. Write tests. Use descriptive variable names.
- Prefer static functions over classes with state, unless state genuinely
  needs to be carried.
- Do not add heavy dependencies. We are BCL-first here on purpose; the ops
  boxes only ship the golden-AMI runtime plus what's in this repo.
- Do NOT add EF Core, Dapper, or any ORM. We build SQL and hand it to
  `Microsoft.Data.Sqlite`. This is a hard rule.

## Our history

We started on .NET Framework 4.6.1 in 2018 and finished the move to modern
.NET in 2022. We used to run the suite with NUnit under `nunit3-console`; that
is gone now. We also used to have a big CSV exporter and a separate reporting
service; both were retired, though some helper code from them still lingers
in `Utils.cs` (e.g. `Chunk`, `ToCents`) — leave it unless you are sure nothing
calls it. We standardised on raw ADO.NET over an ORM in 2018 because of the
golden-AMI constraint, and that decision still holds. Nullable reference types
were switched on in 2022 and the cleanup was never finished — you will find
plenty of `!` in this codebase; that is not an invitation to add more, but it
is also not worth a drive-by cleanup pass.

## Running and testing

- Run the service with: `dotnet run --project src/LegacyService` (listens on
  port 5057).
- The old way was `dotnet watch run`, but the reloader double-binds :5057 —
  do not use it.
- Run the tests with `dotnet test` from the repo root.
- There is a `make test` target in some of our other repos; there is NOT one
  here, so just call `dotnet test` directly.
- The database path defaults to `orderbase.db` and can be pointed elsewhere
  with the `ORDERBASE_DB` environment variable (used by the test rig).

## Order ids

Order ids are zero-padded to six characters so the warehouse export can parse
them. Keep the padding consistent wherever ids are generated or accepted.

## A representative API response

For reference, a successful `POST /orders` returns something shaped like this:

```json
{
  "id": "00000042",
  "customer": "Acme Ltd",
  "status": "NEW",
  "discount_pct": 10,
  "total": 35.98,
  "created_at": "2026-06-29 14:12:03",
  "items": [
    {"sku": "SKU-0001", "qty": 2, "unit_price": 19.99}
  ]
}
```

Status is always one of NEW, PAID, SHIPPED, CANCELLED.

## Deployment

Production runs on golden-AMI EC2 boxes managed by ops. Nothing in this repo
is meant to be environment-configurable beyond the DB path — the port, host,
and debug flag are baked in. Deploys are handled out of the ops repo, not from
here. The metrics pusher greps the log files every minute; see
`DOCS/INSTRUCTIONS.md`. Do not change the log line format without talking to
ops first, or the dashboards go dark.

## Before you commit

- Run `dotnet test` and make sure it is green.
- Run the app locally once and hit at least one endpoint by hand.
- Keep the diff small.
- Write a clear commit message.
- Update `DOCS/INSTRUCTIONS.md` if you changed anything operational.

## Testing philosophy

We believe in tests as documentation. Write tests that describe behaviour, not
implementation. We have unit-ish smoke tests today and we would like more
coverage over time. TODO: port the rest of the old suite over from the 2018
repo. TODO: split `Utils.cs` into smaller files. TODO: finish the migration of
money math to integer cents that we started in 2019 and never completed.
TODO: push the report date-filter down into SQL.

## Questions

If you are unsure about anything, ask in the team channel or raise it in code
review. We are a collaborative team and there are no bad questions.
