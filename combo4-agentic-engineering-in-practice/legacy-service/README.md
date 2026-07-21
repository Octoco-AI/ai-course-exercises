# OrderBase

A small, deliberately dated order-tracking service. Flask + sqlite3 +
stdlib only, written in a 2018 house style (thin tests, `print`/logger mix,
string-formatted SQL) and still running on modern Python (>= 3.10).

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
Module 5 exercise; don't add it here.)

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # or .venv\Scripts\activate on Windows
pip install -e '.[dev]'
./verify.sh                        # sanity check: install, tests, boot, curl
```

Requires Python 3.10+.

---

## Running it

```bash
orderbase                          # console script -> starts on :5057
# or, equivalently:
python -m legacy_service.app
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
python scripts/seed_data.py        # ~30 deterministic orders over 3 days
```

---

## A note on order ids

Order ids are **fixed-width, zero-padded strings** (see
`utils.format_order_id`). A downstream warehouse consumer parses them by
column position, so the width is load-bearing — don't change it, and keep the
padding rule in `app.py`'s `GET /orders/<id>` handler in sync with
`utils.format_order_id`. The exact rule lives in a code comment; treat that
comment as the spec.

---

## The three microtooling chores (Module 10)

OrderBase ships three small, real chores. In Module 10 you turn each into a
reusable command / script instead of doing it by hand:

1. **Log summary.** Parse `logs/app-*.log` and produce a per-endpoint,
   per-day summary (request counts, error counts, slowest lines). The logs are
   deliberately noisy and mixed-format — that's the point.
2. **Version bump.** Bump the version in lockstep across the three places it
   lives: `pyproject.toml`, `src/legacy_service/app.py` (`APP_VERSION`), and
   this README's `Version:` line. Miss one and they drift.
3. **Regenerate fixtures.** Re-create the seed database and the log fixtures
   deterministically, *with validation* (row counts, id widths, totals that
   re-add up). `scripts/seed_data.py` and `scripts/gen_logs.py` are the
   starting points.

---

## Which module uses what

| Module | Uses |
|---|---|
| M4 — agent-assisted testing | `scripts/create-regression-branch.sh`, `.github/workflows/tests.yml` (the CI gate). |
| M6 — context engineering | `CLAUDE.md` (audit target) and `AGENTS.md` (reconcile the two). |
| M7 — MCP in practice | `.mcp.json.sample` (which servers to trust) and `DOCS/INSTRUCTIONS.md` (governance). |
| M8 — working with legacy code | The whole service, plus `FAKE_SENTRY.md` and `logs/`. Main event. |
| M10 — microtooling | The three chores above. |
| M11 — debugging & triage | `logs/` + `FAKE_SENTRY.md` — trace a reported issue to the code. |

---

## Layout

```
legacy-service/
├── src/legacy_service/
│   ├── app.py             ← Flask app, four endpoints
│   ├── orders.py          ← order domain logic
│   ├── db.py              ← sqlite helpers
│   ├── utils.py           ← id formatting, money, date parsing
│   └── logging_setup.py   ← shared logging config
├── tests/test_smoke.py    ← thin smoke tests (on purpose)
├── scripts/
│   ├── seed_data.py       ← deterministic seed data
│   ├── gen_logs.py        ← deterministic log-file generator
│   └── create-regression-branch.sh
├── logs/                  ← sample log fixtures (mixed format, noisy)
├── DOCS/INSTRUCTIONS.md   ← ops runbook
├── FAKE_SENTRY.md         ← three exported issue writeups
├── .mcp.json.sample       ← example MCP server config
├── .github/workflows/tests.yml
├── pyproject.toml
└── verify.sh
```

---

## Testing

```bash
pytest                             # the smoke suite
```

The suite is deliberately thin (it checks the service turns on). Growing it is
part of the point in several modules — don't mistake "green" for "covered."
