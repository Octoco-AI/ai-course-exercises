#!/usr/bin/env bash
#
# Pre-flight check for the OrderBase sample repo.
#
# Checks Python, installs the package (editable), runs the smoke tests, then
# boots the service and hits one endpoint. Non-zero exit if anything fails.
#
# Usage:
#   ./verify.sh

set -u

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

pass() { printf "${GREEN}PASS %s${NC}\n" "$1"; }
fail() { printf "${RED}FAIL %s${NC}\n" "$1"; FAILED=1; }
warn() { printf "${YELLOW}WARN %s${NC}\n" "$1"; }

FAILED=0
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo "=== OrderBase pre-flight ==="
echo

# Python 3.10+
if command -v python3 >/dev/null; then
    PY_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    PY_MINOR=$(python3 -c 'import sys; print(sys.version_info[1])')
    PY_MAJOR=$(python3 -c 'import sys; print(sys.version_info[0])')
    if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 10 ]; then
        pass "Python $PY_VERSION"
    else
        fail "Python $PY_VERSION is too old (need 3.10+)"
    fi
else
    fail "python3 not found"
fi

# Editable install
echo
echo "=== Installing (pip install -e '.[dev]') ==="
if python3 -m pip install -q -e '.[dev]'; then
    pass "editable install"
else
    fail "editable install failed"
fi

# Smoke tests
echo
echo "=== Running smoke tests ==="
python3 -m pytest -q
if [ "$?" -eq 0 ]; then
    pass "smoke tests"
else
    fail "smoke tests failed"
fi

# Boot the service and hit one endpoint. Run from a scratch dir with a scratch
# DB so we don't leave orderbase.db or a log file behind in the repo.
echo
echo "=== Booting service and probing GET /orders?limit=1 ==="
BOOT_DIR="$(mktemp -d -t orderbase-verify)"
export ORDERBASE_DB="$BOOT_DIR/verify.db"
( cd "$BOOT_DIR" && python3 -m legacy_service.app ) >"$BOOT_DIR/app.log" 2>&1 &
APP_PID=$!
trap 'kill "$APP_PID" 2>/dev/null; rm -rf "$BOOT_DIR"' EXIT

# Wait for the port to answer (up to ~15s).
CODE=""
for _ in $(seq 1 30); do
    CODE=$(curl -s -o /dev/null -w '%{http_code}' 'http://localhost:5057/orders?limit=1' 2>/dev/null || true)
    if [ "$CODE" = "200" ]; then
        break
    fi
    if ! kill -0 "$APP_PID" 2>/dev/null; then
        break
    fi
    sleep 0.5
done

if [ "$CODE" = "200" ]; then
    pass "GET /orders?limit=1 -> 200"
else
    fail "GET /orders?limit=1 -> ${CODE:-no response}"
    echo "--- app output ---"
    cat "$BOOT_DIR/app.log" 2>/dev/null | tail -20
fi

echo
if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}Ready. Start the service with: orderbase (or python -m legacy_service.app)${NC}"
    exit 0
else
    echo -e "${RED}Some checks failed.${NC}"
    exit 1
fi
