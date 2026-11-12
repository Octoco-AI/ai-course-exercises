#!/usr/bin/env bash
#
# Pre-flight check for the OrderBase assessment practice app.
#
# Checks Python, installs the package (editable), runs the tests, then boots
# the service on loopback and hits two endpoints. Non-zero exit if anything
# fails.
#
# Usage:
#   ./verify.sh                 # install, test, boot, probe
#   ./verify.sh --no-install    # skip pip (already installed, or offline)

set -u

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

pass() { printf "${GREEN}PASS %s${NC}\n" "$1"; }
fail() { printf "${RED}FAIL %s${NC}\n" "$1"; FAILED=1; }

FAILED=0
INSTALL=1
[ "${1:-}" = "--no-install" ] && INSTALL=0

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

PORT="${ORDERBASE_PORT:-5057}"
BASE="http://127.0.0.1:$PORT"

echo "=== OrderBase pre-flight ==="
echo

# Python 3.10+
if command -v python3 >/dev/null; then
    PY_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
        pass "Python $PY_VERSION"
    else
        fail "Python $PY_VERSION is too old (need 3.10+)"
    fi
else
    fail "python3 not found"
    exit 1
fi

if [ "$INSTALL" -eq 1 ]; then
    echo
    echo "=== Installing (pip install -e '.[dev]') ==="
    if python3 -m pip install -q -e '.[dev]'; then
        pass "editable install"
    else
        fail "editable install failed"
    fi
fi

echo
echo "=== Running tests ==="
if python3 -m pytest -q; then
    pass "tests"
else
    fail "tests failed"
fi

# Refuse to probe if something else already owns the port, or we would be
# testing the wrong service.
if curl -s -o /dev/null --max-time 1 "$BASE/health" 2>/dev/null; then
    fail "port $PORT is already in use; stop the other service or set ORDERBASE_PORT"
else
    # Boot from a scratch dir with a scratch DB so nothing is left behind.
    # PYTHONPATH pins this copy of the package: the combo 4 OrderBase uses the
    # same package name, and an environment with both installed would
    # otherwise boot whichever was installed last.
    echo
    echo "=== Booting service on 127.0.0.1:$PORT and probing ==="
    BOOT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/orderbase-verify.XXXXXX")"
    ( cd "$BOOT_DIR" && PYTHONPATH="$REPO_ROOT/src" \
        ORDERBASE_DB="$BOOT_DIR/verify.db" ORDERBASE_HOST=127.0.0.1 \
        ORDERBASE_PORT="$PORT" python3 -m legacy_service.app ) >"$BOOT_DIR/app.log" 2>&1 &
    APP_PID=$!
    trap 'kill "$APP_PID" 2>/dev/null; rm -rf "$BOOT_DIR"' EXIT

    CODE=""
    for _ in $(seq 1 30); do
        CODE=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/health" 2>/dev/null || true)
        [ "$CODE" = "200" ] && break
        kill -0 "$APP_PID" 2>/dev/null || break
        sleep 0.5
    done

    if [ "$CODE" = "200" ]; then
        pass "GET /health -> 200"
        # Local demo account seeded by db.init_db (see README).
        DEMO_USER_TOKEN=alice-dev-token
        CODE=$(curl -s -o /dev/null -w '%{http_code}' \
            -H "Authorization: Bearer $DEMO_USER_TOKEN" "$BASE/orders?limit=1")
        if [ "$CODE" = "200" ]; then
            pass "GET /orders?limit=1 (as alice) -> 200"
        else
            fail "GET /orders?limit=1 (as alice) -> $CODE"
        fi
    else
        fail "GET /health -> ${CODE:-no response}"
        echo "--- app output ---"
        tail -20 "$BOOT_DIR/app.log" 2>/dev/null
    fi
fi

echo
if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}Ready. Start the service with: orderbase (or python -m legacy_service.app)${NC}"
    exit 0
else
    echo -e "${RED}Some checks failed.${NC}"
    exit 1
fi
