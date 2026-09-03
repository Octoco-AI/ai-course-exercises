# OrderBase (TypeScript)

A small, deliberately dated order-tracking service. Express + the built-in
`node:sqlite` only, written in a 2018 house style (no classes, no `async` in
the domain layer, hand-built SQL) and still running on modern Node (22.13+).

This is the **TypeScript path**. Python is the workshop's main path and the
exercise text uses Python code blocks; this repo is here so a Node/TS team
can spend the legacy-code modules on their own stack instead of translating
on the fly. The [C# path](../../csharp/legacy-service-csharp/) is the same
service again, and the [Python original](../../python/legacy-service/) is
the canonical one all three copies are ported from.

> **You do not need to know Python to do the legacy-code exercises.**
> Everything below — the seeded bugs, the load-bearing quirk, the smells —
> exists here in TypeScript, and the fixtures (logs, the fake Sentry issues,
> the seed data) were regenerated from this port's own source, not copied.

OrderBase is a **teaching artifact** for the *Advanced Agentic Engineering*
workshop. It stands in for "the ugly backend service your team is scared to
touch." It has real domain logic, real logs, and a couple of real production
smells. You will read it, extend it, test it, and refactor it — and it is the
neutral-ground fallback whenever an exercise asks for a repo you'd rather not
practise on.

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
`GET /orders?limit=1` as a liveness probe. Leave it that way; its absence is
one of the things worth noticing when you map the service.

---

## Setup

```bash
npm install
./verify.sh
```

Requires **Node 22.13 or later** — the exercise uses the built-in
`node:sqlite`, which needs no `--experimental-sqlite` flag from that patch
onward. Run `node --version` if you're not sure which you have.

---

## Running it

```bash
npm start                          # -> starts on :5057
```

The server binds `0.0.0.0:5057`. On boot it creates `orderbase.db` in the
working directory and (if a `logs/` dir exists) appends to
`logs/app-YYYY-MM-DD.log`. You'll see one `ExperimentalWarning` line about
sqlite on boot — that's expected (see `DOCS/INSTRUCTIONS.md`), not a bug.

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
npm run seed-data                  # ~30 deterministic orders over 3 days
```

---

## A note on order ids

Order ids are **fixed-width, zero-padded strings** (see
`utils.formatOrderId`). A downstream warehouse consumer parses them by column
position, so the width is load-bearing — don't change it, and keep the
padding rule in `app.ts`'s `GET /orders/:orderId` handler in sync with
`utils.formatOrderId`. The exact rule lives in a code comment; treat that
comment as the spec.

---

## Optional chores

OrderBase ships three small, real chores. None of them is a required exercise
step — they're here if you want extra ground to practise on, or a candidate to
turn into a reusable skill:

1. **Log summary.** Parse `logs/app-*.log` and produce a per-endpoint,
   per-day summary (request counts, error counts, slowest lines). The logs are
   deliberately noisy and mixed-format — that's the point.
2. **Version bump.** Bump the version in lockstep across the three places it
   lives: `package.json`, `src/app.ts` (`APP_VERSION`), and this README's
   `Version:` line. Miss one and they drift.
3. **Regenerate fixtures.** Re-create the seed database and the log fixtures
   deterministically, *with validation* (row counts, id widths, totals that
   re-add up). `scripts/seedData.ts` and `scripts/genLogs.ts` are the
   starting points.

---

## Which module uses what

| Module | Uses |
|---|---|
| M16 — context engineering | `CLAUDE.md` (audit target — it is deliberately bloated) and `AGENTS.md`. The two files **contradict each other**; reconciling them is the exercise. |
| M17 — MCP for teams | `.mcp.json.sample` (which servers to trust) and `DOCS/INSTRUCTIONS.md` (governance, and a hardcoded key). |
| M18 — working with legacy code | The whole service. Main event: `src/orders.ts` is untested, `utils.ts` carries the refactor targets. |
| M19 — patterns: promote vs discourage | The rule candidates: `console.log` vs the hand-rolled logger, template-literal SQL, hardcoded config with no dotenv, duplicate helpers, the committed key. |
| M20 — security, governance, agent inventory | `.mcp.json.sample` + `DOCS/INSTRUCTIONS.md` as inventory rows. |

`FAKE_SENTRY.md` and `logs/` are extra material — three exported issue
writeups and noisy log fixtures. Nothing requires them, but they're the
realistic texture if you want to trace a reported symptom back to the code.

---

## Layout

```
legacy-service-ts/
├── src/
│   ├── app.ts               ← Express app (module-level singleton), four endpoints
│   ├── server.ts            ← boots app.ts -- logging + db init live here, not in app.ts
│   ├── orders.ts            ← order domain logic
│   ├── db.ts                ← node:sqlite helpers
│   ├── utils.ts             ← id formatting, money, date parsing
│   └── loggingSetup.ts      ← hand-rolled logging config
├── tests/
│   └── smoke.test.ts        ← thin smoke tests (on purpose)
├── scripts/
│   ├── seedData.ts          ← deterministic seed data
│   ├── genLogs.ts           ← deterministic log-file generator
│   └── create-regression-branch.sh
├── logs/                    ← sample log fixtures (mixed format, noisy)
├── DOCS/INSTRUCTIONS.md     ← ops runbook
├── FAKE_SENTRY.md           ← three exported issue writeups
├── .mcp.json.sample         ← example MCP server config
├── .github/workflows/tests.yml
├── package.json / tsconfig.json / vitest.config.ts
└── verify.sh
```

---

## Testing

```bash
npm test                            # the smoke suite
```

The suite is deliberately thin (it checks the service turns on). Growing it is
part of the point in several modules — don't mistake "green" for "covered."

---

## Two things that differ from the Python path

1. **`money()` isn't bit-for-bit identical to Python's `round()`.** Both
   round money the "wrong" way on purpose (that's the seeded bug), but
   JavaScript's floats don't preserve the same intermediate precision Python's
   do, so this port's rounding rule diverges from Python on **one** of the 30
   seeded orders (order #16: 0.93 here vs 0.94 in Python and C#). Every bug
   probe used in the exercises and in `FAKE_SENTRY.md` still reproduces
   exactly — see `FACILITATOR.md` if you're curious which order and why.
2. **The app is split into `app.ts` and `server.ts`.** Python's `app.py`
   does both in one file; here, importing the Express app for tests must not
   also boot logging or touch the database, so that split is structural, not
   cosmetic. If you add a fifth endpoint, it goes in `app.ts`; if you add
   another thing that runs once at startup, it goes in `server.ts`.

---

## Post-workshop

1. **Port to a typed request body.** Swap the hand-parsed `unknown` body in
   `createOrder` for a validated shape and see how much of the hand-rolled
   validation logic disappears — and how much of the "bad item" test coverage
   goes with it.
2. **Grow the test suite.** Three smoke tests is a floor, not a ceiling.
3. **Try Zod or a JSON-schema validator** on top of the request body, as a
   stretch goal for pairs who finish early — and notice how much of `utils.ts`
   it makes redundant.
