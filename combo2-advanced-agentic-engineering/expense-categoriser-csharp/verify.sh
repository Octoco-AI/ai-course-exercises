#!/usr/bin/env bash
#
# Pre-flight check. Run this 48 hours before the workshop.
#
# What it checks:
#   - The .NET SDK 10+ is available.
#   - The solution builds.
#   - The unit + API tests pass (no API key needed — the LLM is mocked).
#   - A GOOGLE_API_KEY is set (warning only; unit tests don't need it).
#
# With --evals it additionally runs the real eval suite: ~22 Gemini calls,
# about 30 seconds and roughly $0.01.
#
# If all checks pass, you are ready for M11 and M12.
#
# On Windows you can run verify.ps1 instead — the C# path does not need WSL.

set -u

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

pass() { printf "${GREEN}✅ %s${NC}\n" "$1"; }
fail() { printf "${RED}❌ %s${NC}\n" "$1"; FAILED=1; }
warn() { printf "${YELLOW}⚠️  %s${NC}\n" "$1"; }

FAILED=0
RUN_EVALS=0

for arg in "$@"; do
    case "$arg" in
        --evals) RUN_EVALS=1 ;;
        --help|-h) sed -n '2,16p' "$0"; exit 0 ;;
        *) echo "Unknown arg: $arg" >&2; exit 2 ;;
    esac
done

echo "=== Expense Categoriser (C#) pre-flight check ==="
echo

# .NET SDK version
if command -v dotnet >/dev/null; then
    SDK_VERSION=$(dotnet --version 2>/dev/null)
    SDK_MAJOR=${SDK_VERSION%%.*}
    if [ "${SDK_MAJOR:-0}" -ge 10 ] 2>/dev/null; then
        pass ".NET SDK $SDK_VERSION (>= 10 required)"
    else
        fail ".NET SDK $SDK_VERSION is too old. Install .NET 10+ from https://dotnet.microsoft.com/download"
    fi
else
    fail "dotnet not found. Install the .NET SDK 10+ from https://dotnet.microsoft.com/download"
fi

# Build
if [ "$FAILED" -eq 0 ]; then
    if dotnet build --nologo -v quiet >/dev/null 2>&1; then
        pass "solution builds"
    else
        fail "build failed. Run 'dotnet build' to see why."
    fi
fi

# Unit + API tests — these need no key.
if [ "$FAILED" -eq 0 ]; then
    TEST_LOG=$(mktemp)
    if dotnet test --no-build --nologo --filter "Category!=Evals" >"$TEST_LOG" 2>&1; then
        COUNTS=$(grep -oE 'Passed:[[:space:]]+[0-9]+' "$TEST_LOG" | tail -1)
        pass "unit + API tests pass (${COUNTS:-all})"
    else
        fail "unit + API tests failed. Run: dotnet test --filter \"Category!=Evals\""
        tail -20 "$TEST_LOG" | sed 's/^/    /'
    fi
    rm -f "$TEST_LOG"
fi

# API key — a warning, not a failure. The unit tests mock the LLM.
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
fi

if [ -n "${GOOGLE_API_KEY:-}" ] && [ "${GOOGLE_API_KEY}" != "your_gemini_api_key_here" ]; then
    pass "GOOGLE_API_KEY is set"
else
    warn "GOOGLE_API_KEY not set. Unit tests don't need it, but M12's eval run does. Copy .env.example to .env before the workshop."
fi

# Opt-in: the real eval suite.
if [ "$RUN_EVALS" -eq 1 ] && [ "$FAILED" -eq 0 ]; then
    echo
    if [ -z "${GOOGLE_API_KEY:-}" ] || [ "${GOOGLE_API_KEY}" = "your_gemini_api_key_here" ]; then
        fail "--evals needs a real GOOGLE_API_KEY in .env"
    else
        echo "Running the eval suite against the real model (~30s, ~\$0.01)..."
        if dotnet test --no-build --nologo --filter "Category=Evals" --logger "console;verbosity=detailed" 2>&1 | tail -30; then
            pass "eval suite passed"
        else
            fail "eval suite failed — see the output above"
        fi
    fi
fi

echo
if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}All checks passed — you are ready for M11 and M12.${NC}"
    exit 0
else
    echo -e "${RED}Some checks failed. Fix the items above and re-run.${NC}"
    exit 1
fi
