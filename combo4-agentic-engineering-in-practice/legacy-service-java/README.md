# OrderBase (Java)

A small, deliberately dated order-tracking service. Spring Boot for HTTP
routing only + `sqlite-jdbc` for raw JDBC, written in a 2018 house style (no
DI beyond the controller, no ORM, hand-built SQL) and still running on modern
Java (21+).

This is the **Java path**. Python is the workshop's main path and the
exercise text uses Python code blocks; this repo is here so a JVM team can
spend the legacy-code modules on their own stack instead of translating on
the fly. The [C# path](../../csharp/legacy-service-csharp/) and
[TypeScript path](../../typescript/legacy-service-ts/) are the same service
again, and the [Python original](../../python/legacy-service/) is the
canonical one all three copies are ported from.

> **You do not need to know Python to do the legacy-code exercises.**
> Everything below — the seeded bugs, the load-bearing quirk, the smells —
> exists here in Java, and the fixtures (logs, the fake Sentry issues, the
> seed data) were regenerated from this port's own source, not copied.

OrderBase is a **teaching artifact** for Combo 4 — *Agentic Engineering in
Practice*. It stands in for "the ugly backend service your team is scared to
touch." It has real domain logic, real logs, and a couple of real production
smells. You will read it, extend it, test it, and refactor it across several
modules.

**Version: 1.4.2**

---

## What it does

Four HTTP endpoints over a two-table sqlite schema (`orders`, `order_items`):

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/orders` | Create an order (customer + line items + optional discount). |
| `GET` | `/orders/<id>` | Fetch one order by id. Bare numbers (`42`) are accepted and padded. |
| `GET` | `/orders` | List orders (`?status=` and `?limit=` filters). |
| `GET` | `/report` | Order count + totals for a day (`?date=YYYY-MM-DD`, defaults to today). |

There is intentionally **no `/health` endpoint** — monitoring hits
`GET /orders?limit=1` as a liveness probe. (Adding a real health check is a
Module 24 exercise; don't add it here.)

---

## Setup

```bash
./mvnw -q package -DskipTests
./verify.sh                  # macOS / Linux / WSL
pwsh ./verify.ps1            # Windows, PowerShell 7+
```

Requires JDK 21+. No system Maven install needed — the wrapper (`./mvnw`)
downloads Maven itself on first run.

> **Windows attendees:** this path needs no WSL. Run it natively in PowerShell 7+.

---

## Running it

```bash
./mvnw spring-boot:run     # -> starts on :5057
```

The server binds `0.0.0.0:5057`. On boot it creates `orderbase.db` in the
working directory and (if a `logs/` dir exists) appends to
`logs/app-YYYY-MM-DD.log`.

Hit it:

```bash
# create an order
curl -sS -X POST http://localhost:5057/orders \
  -H 'Content-Type: application/json' \
  -d '{"customer":"Acme Ltd","items":[{"sku":"SKU-0001","qty":2,"unit_price":19.99}],"discount_pct":10}'

# fetch it back (bare id is padded to 8 chars)
curl -sS http://localhost:5057/orders/1

# list PAID orders
curl -sS 'http://localhost:5057/orders?status=PAID&limit=20'

# daily report
curl -sS 'http://localhost:5057/report?date=2026-06-29'
```

Seed some data first so the list and report endpoints have something to show:

```bash
./mvnw -q exec:java -Dexec.mainClass=ai.octoco.legacyservice.tools.SeedData
# ~30 deterministic orders over 3 days
```

---

## A note on order ids

Order ids are **fixed-width, zero-padded strings** (see
`Utils.formatOrderId`). A downstream warehouse consumer parses them by column
position, so the width is load-bearing — don't change it, and keep the
padding rule in `LegacyServiceApplication.java`'s `GET /orders/{orderId}`
handler in sync with `Utils.formatOrderId`. The exact rule lives in a code
comment; treat that comment as the spec.

---

## Optional chores

OrderBase ships three small, real chores. None of them is a required exercise
step — they're here if you want extra ground to practise on, or a candidate to
turn into a reusable skill:

1. **Log summary.** Parse `logs/app-*.log` and produce a per-endpoint,
   per-day summary (request counts, error counts, slowest lines). The logs are
   deliberately noisy and mixed-format — that's the point.
2. **Version bump.** Bump the version in lockstep across the three places it
   lives: `pom.xml` (`<version>`), `LegacyServiceApplication.java`
   (`APP_VERSION`), and this README's `Version:` line. Miss one and they
   drift.
3. **Regenerate fixtures.** Re-create the seed database and the log fixtures
   deterministically, *with validation* (row counts, id widths, totals that
   re-add up). `ai.octoco.legacyservice.tools.SeedData` and
   `ai.octoco.legacyservice.tools.GenLogs` are the starting points.

---

## Which module uses what

| Module | Uses |
|---|---|
| M16 — context engineering | `CLAUDE.md` (audit target — it is deliberately bloated) and `AGENTS.md`. The two files **contradict each other**; reconciling them is the exercise. |
| M17 — MCP for teams | `.mcp.json.sample` (which servers to trust) and `DOCS/INSTRUCTIONS.md` (governance, and a hardcoded key). |
| M18 — working with legacy code | The whole service. Main event: `Orders.java` is untested, `Utils.java` carries the refactor targets. |
| M19 — patterns: promote vs discourage | The rule candidates: `System.out.println` vs the hand-rolled logger, string-interpolated SQL, `DEBUG = true`, duplicate helpers, the committed key. |
| M20 — security, governance, agent inventory | `.mcp.json.sample` + `DOCS/INSTRUCTIONS.md` as inventory rows. |

`FAKE_SENTRY.md` and `logs/` are extra material — three exported issue
writeups and noisy log fixtures. Nothing requires them, but they're the
realistic texture if you want to trace a reported symptom back to the code.

---

## Layout

```
legacy-service-java/
├── src/main/java/ai/octoco/legacyservice/
│   ├── LegacyServiceApplication.java  ← Spring Boot app + REST controller, four endpoints
│   ├── Orders.java                    ← order domain logic
│   ├── Db.java                        ← sqlite-jdbc helpers
│   ├── Utils.java                     ← id formatting, money, date parsing
│   ├── LoggingSetup.java / Logger.java ← hand-rolled logging config
│   └── tools/
│       ├── SeedData.java              ← deterministic seed data
│       └── GenLogs.java               ← deterministic log-file generator
├── src/test/java/ai/octoco/legacyservice/
│   └── LegacyServiceSmokeTests.java   ← thin smoke tests (on purpose)
├── scripts/
│   └── create-regression-branch.sh / .ps1
├── logs/                   ← sample log fixtures (mixed format, noisy)
├── DOCS/INSTRUCTIONS.md    ← ops runbook
├── FAKE_SENTRY.md          ← three exported issue writeups
├── .mcp.json.sample        ← example MCP server config
├── .github/workflows/tests.yml
├── pom.xml / mvnw / mvnw.cmd
└── verify.sh / verify.ps1
```

---

## Testing

```bash
./mvnw test                        # the smoke suite
```

The suite is deliberately thin (it checks the service turns on). Growing it is
part of the point in several modules — don't mistake "green" for "covered."

---

## Two things that differ from the Python path

1. **No dynamic-language flexibility at the JSON boundary.** Python's
   `request.get_json()` hands you a plain dict; `POST /orders` here parses a
   raw Jackson `JsonNode` by hand instead of binding to a DTO, on purpose — a
   strict record type would auto-validate the shape and quietly remove the
   hand-rolled validation that M19 uses as a rule candidate.
2. **`sqlite-jdbc` accepts bare `?` placeholders natively** — unlike the C#
   port, which has to rewrite `Microsoft.Data.Sqlite`'s named `@pN`
   parameters, `Db.java`'s `query`/`execute` helpers bind straight onto
   `PreparedStatement` with no translation layer.

---

## Post-workshop

1. **Port to a typed client.** Swap the hand-parsed `JsonNode` body for a
   validated DTO and see how much of the hand-rolled validation logic
   disappears — and how much of the "bad item" test coverage goes with it.
2. **Grow the test suite.** Three smoke tests is a floor, not a ceiling.
3. **Try Spring AI** on top of the reconcile-cron logic described in
   `DOCS/INSTRUCTIONS.md`, as a stretch goal for pairs who finish early.
