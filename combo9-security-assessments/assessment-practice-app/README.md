# OrderBase — assessment practice app

OrderBase is a small order-tracking API (Flask + sqlite3) used as the
practice target in the hands-on security assessment session. You will run
scanners over it, review it with an agent, and write up what you find.

> **This app is deliberately weak.** It contains planted security
> weaknesses for training. Run it on your own machine only, never deploy
> it, and do not copy its code into a real project. It binds to
> `127.0.0.1` by default; leave it that way.

Finding the weaknesses is the exercise, so this README does not list them.
It tells you how the service is *meant* to work. Comparing that intent with
what the code actually does is a large part of the job.

**Version: 1.5.0**

---

## How it is meant to work

Every request except the health check carries a bearer token:
`Authorization: Bearer <token>`. There are two roles.

- **Customers** create orders and track their own. They may change the
  delivery contact name (`customer`) on an order that is still `NEW`, and
  may cancel their own `NEW` orders. They may not apply discounts.
- **Staff** can see and change any order, apply discounts, and cancel `NEW`
  or `PAID` orders. The nightly fulfilment sync runs as a staff-level
  service account and pushes status updates.
- The **daily report** is for the finance team, who are staff.

Order statuses are `NEW`, `PAID`, `SHIPPED` and `CANCELLED`. Order ids are
fixed-width, zero-padded strings (`00000042`); bare numbers (`42`) are
accepted and padded.

### Local demo accounts

An empty database is seeded with three demo accounts so you can use the
service straight away. They exist only in your local database.

| User | Role | Token |
|---|---|---|
| Alice | customer | `alice-dev-token` |
| Bob | customer | `bob-dev-token` |
| Sam | staff | `staff-dev-token` |

### Routes

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness check. |
| `POST` | `/orders` | Create an order (customer name + line items, optional discount). |
| `GET` | `/orders` | List orders (`?status=`, `?limit=`). |
| `GET` | `/orders/<id>` | Fetch one order. |
| `PATCH` | `/orders/<id>` | Edit an order. |
| `POST` | `/orders/<id>/cancel` | Cancel an order. |
| `GET` | `/report` | Order count and totals for a day (`?date=YYYY-MM-DD`, defaults to today). |

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # or .venv\Scripts\activate on Windows
pip install -e '.[dev]'
./verify.sh                        # install, tests, boot on loopback, probe
```

Requires Python 3.10+. `./verify.sh --no-install` skips the `pip` step if
you have already installed, or are offline.

Use a fresh virtualenv. The package is called `legacy_service`, the same
name as the OrderBase used in other workshops, and two copies in one
environment will shadow each other.

## Running it

```bash
orderbase                          # console script, listens on 127.0.0.1:5057
# or, equivalently:
python -m legacy_service.app
```

On boot it creates `orderbase.db` in the working directory. Try it:

```bash
ALICE="alice-dev-token"

# create an order as Alice
curl -sS -X POST http://127.0.0.1:5057/orders \
  -H "Authorization: Bearer $ALICE" -H 'Content-Type: application/json' \
  -d '{"customer":"Alice","items":[{"sku":"SKU-0001","qty":2,"unit_price":19.99}]}'

# fetch it back, then list Alice's orders
curl -sS -H "Authorization: Bearer $ALICE" http://127.0.0.1:5057/orders/1
curl -sS -H "Authorization: Bearer $ALICE" 'http://127.0.0.1:5057/orders?limit=20'
```

### Configuration

All settings come from the environment (see `.env.example`).

| Variable | Default | Meaning |
|---|---|---|
| `ORDERBASE_HOST` | `127.0.0.1` | Interface to listen on. |
| `ORDERBASE_PORT` | `5057` | Port. |
| `ORDERBASE_DB` | `orderbase.db` | sqlite file. |
| `ORDERBASE_DEBUG` | `0` | `1` turns on Flask debug mode. Leave it off. |
| `ORDERBASE_DEMO_USERS` | `1` | `0` skips seeding the demo accounts. |
| `ORDERBASE_WMS_SYNC_TOKEN` | — | Service token for the fulfilment sync. |

## Testing

```bash
pytest
```

The tests need no network. Green tests mean the service works as tested,
which is not the same thing as secure.

---

## What is in scope

Everything in this directory: the Python source, the tests, the
dependency pins, the `Dockerfile` and the CI workflow under
`.github/workflows/`. GitHub only runs workflows from a repository's root,
so the workflow does not run from here; review it as if it did.

You do not need to build the container image. If you do, publish the port
to loopback only:

```bash
docker build -t orderbase .
docker run --rm -p 127.0.0.1:5057:5057 orderbase
```

Point your scanners and agents at this directory and at
`http://127.0.0.1:5057` only, never at anything else.

## Layout

```
assessment-practice-app/
├── src/legacy_service/
│   ├── app.py             ← Flask app and routes
│   ├── auth.py            ← bearer-token authentication
│   ├── orders.py          ← order domain logic
│   ├── db.py              ← sqlite helpers, schema, demo accounts
│   ├── config.py          ← settings from the environment
│   ├── utils.py           ← ids, money, dates, token hashing
│   └── logging_setup.py   ← shared logging config
├── tests/                 ← smoke and access tests
├── requirements.txt       ← pinned runtime dependencies for the image
├── Dockerfile
├── .github/workflows/ci.yml
├── .env.example
├── pyproject.toml
└── verify.sh
```
