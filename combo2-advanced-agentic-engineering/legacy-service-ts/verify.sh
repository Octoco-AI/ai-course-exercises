#!/usr/bin/env bash
#
# Pre-flight check for the OrderBase (TypeScript) sample repo.
#
# Checks Node, installs status, typechecks, runs the smoke tests, then boots
# the service and hits one endpoint. Non-zero exit if anything fails.
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

echo "=== OrderBase (TypeScript) pre-flight ==="
echo

# Node 22.13+ -- this exercise uses the built-in node:sqlite, which needs no
# --experimental-sqlite flag from 22.13 onward. That's a patch-level floor
# INSIDE the Node 22 the other TS exercises already ask for.
if command -v node >/dev/null; then
    NODE_VERSION=$(node --version)
    NODE_MAJOR=${NODE_VERSION#v}; NODE_MAJOR=${NODE_MAJOR%%.*}
    NODE_REST=${NODE_VERSION#v*.}; NODE_MINOR=${NODE_REST%%.*}
    if [ "${NODE_MAJOR:-0}" -gt 22 ] 2>/dev/null || { [ "${NODE_MAJOR:-0}" -eq 22 ] && [ "${NODE_MINOR:-0}" -ge 13 ]; } 2>/dev/null; then
        pass "Node $NODE_VERSION (>= 22.13.0 required for node:sqlite)"
    else
        fail "Node $NODE_VERSION is too old for node:sqlite. Install Node 22.13+ (or 24 LTS) from https://nodejs.org"
    fi
else
    fail "node not found. Install Node 22.13+ from https://nodejs.org"
fi

# Dependencies
if [ "$FAILED" -eq 0 ]; then
    if [ -d node_modules ]; then
        pass "dependencies installed"
    else
        fail "node_modules missing. Run: npm install"
    fi
fi

# Typecheck
if [ "$FAILED" -eq 0 ]; then
    if npm run --silent typecheck >/dev/null 2>&1; then
        pass "project typechecks"
    else
        fail "typecheck failed. Run 'npm run typecheck' to see why."
    fi
fi

# Smoke tests
if [ "$FAILED" -eq 0 ]; then
    if npm test >/dev/null 2>&1; then
        pass "smoke tests"
    else
        fail "smoke tests failed. Run 'npm test' to see why."
    fi
fi

# Boot the service and hit one endpoint. Run from a scratch dir with a scratch
# DB so we don't leave orderbase.db or a log file behind in the repo.
echo
echo "=== Booting service and probing GET /orders?limit=1 ==="
BOOT_DIR="$(mktemp -d -t orderbase-verify)"
export ORDERBASE_DB="$BOOT_DIR/verify.db"
( cd "$BOOT_DIR" && "$REPO_ROOT/node_modules/.bin/tsx" "$REPO_ROOT/src/server.ts" ) >"$BOOT_DIR/app.log" 2>&1 &
APP_PID=$!
trap 'kill "$APP_PID" 2>/dev/null; rm -rf "$BOOT_DIR"' EXIT

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
    tail -20 "$BOOT_DIR/app.log" 2>/dev/null
fi

echo
if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}Ready. Start the service with: npm start${NC}"
    exit 0
else
    echo -e "${RED}Some checks failed.${NC}"
    exit 1
fi
