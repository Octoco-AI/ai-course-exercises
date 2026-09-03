#!/usr/bin/env bash
#
# Pre-flight check for the OrderBase (C#) sample repo.
#
# Checks the .NET SDK, builds the solution, runs the smoke tests, then boots
# the service and hits one endpoint. Non-zero exit if anything fails.
#
# Usage:
#   ./verify.sh
#
# On Windows you can run verify.ps1 instead -- the C# path does not need WSL.

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

echo "=== OrderBase (C#) pre-flight ==="
echo

# .NET SDK 10+
if command -v dotnet >/dev/null; then
    SDK_VERSION=$(dotnet --version 2>/dev/null)
    SDK_MAJOR=${SDK_VERSION%%.*}
    if [ "${SDK_MAJOR:-0}" -ge 10 ] 2>/dev/null; then
        pass ".NET SDK $SDK_VERSION (>= 10 required)"
    else
        fail ".NET SDK $SDK_VERSION is too old. Install .NET 10 or later from https://dotnet.microsoft.com/download"
    fi
else
    fail "dotnet not found. Install the .NET SDK 10+ from https://dotnet.microsoft.com/download"
fi

# Build
echo
echo "=== Building (dotnet build) ==="
if dotnet build --nologo -v quiet >/dev/null 2>&1; then
    pass "solution builds"
else
    fail "build failed. Run 'dotnet build' to see why."
fi

# Smoke tests
echo
echo "=== Running smoke tests ==="
if dotnet test --no-restore --nologo -v quiet >/dev/null 2>&1; then
    pass "smoke tests"
else
    fail "smoke tests failed"
fi

# Boot the service and hit one endpoint. Run from a scratch dir with a scratch
# DB so we don't leave orderbase.db or a log file behind in the repo.
echo
echo "=== Booting service and probing GET /orders?limit=1 ==="
APP_DLL="$(find src/LegacyService/bin -name 'legacy-service.dll' -path '*/Debug/*' 2>/dev/null | head -1)"
if [ -z "$APP_DLL" ]; then
    fail "could not find the built app (src/LegacyService/bin/Debug/**/legacy-service.dll). Run 'dotnet build' first."
else
    BOOT_DIR="$(mktemp -d -t orderbase-verify)"
    export ORDERBASE_DB="$BOOT_DIR/verify.db"
    ( cd "$BOOT_DIR" && dotnet "$REPO_ROOT/$APP_DLL" ) >"$BOOT_DIR/app.log" 2>&1 &
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
fi

echo
if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}Ready. Start the service with: dotnet run --project src/LegacyService${NC}"
    exit 0
else
    echo -e "${RED}Some checks failed.${NC}"
    exit 1
fi
