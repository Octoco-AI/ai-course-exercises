#!/usr/bin/env bash
#
# Pre-flight check. Run this 48 hours before the workshop.
#
# What it checks:
#   - The .NET SDK 10+ is available.
#   - The solution builds.
#   - The tool tests fail (they should — you haven't written the tools yet)
#     and the reference implementation passes.
#   - A GOOGLE_API_KEY is set (in .env or the environment).
#   - A simple Gemini call succeeds.
#
# If all checks pass, you are ready for M8.
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

echo "=== Tiny Agent (C#) pre-flight check ==="
echo

# .NET SDK version
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
if [ "$FAILED" -eq 0 ]; then
    if dotnet build --nologo -v quiet >/dev/null 2>&1; then
        pass "solution builds"
    else
        fail "build failed. Run 'dotnet build' to see why."
    fi
fi

# The reference implementation must pass its own tests.
if [ "$FAILED" -eq 0 ]; then
    if TINY_AGENT_IMPL=reference dotnet test --nologo -v quiet >/dev/null 2>&1; then
        pass "reference implementation passes all tests"
    else
        fail "reference tests failed — that shouldn't happen. Email workshops@octoco.ai with the output of: TINY_AGENT_IMPL=reference dotnet test"
    fi
fi

# Your own tests are EXPECTED to fail before the workshop.
if [ "$FAILED" -eq 0 ]; then
    if dotnet test --nologo -v quiet >/dev/null 2>&1; then
        warn "your tool tests already pass — have you done the exercise already? (that's fine)"
    else
        pass "your tool tests fail as expected (you write them in M8)"
    fi
fi

# API key present
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
fi

if [ -n "${GOOGLE_API_KEY:-}" ] && [ "${GOOGLE_API_KEY}" != "your_gemini_api_key_here" ]; then
    pass "GOOGLE_API_KEY is set"
else
    fail "GOOGLE_API_KEY not set. Copy .env.example to .env and add your key (https://aistudio.google.com/apikey)"
fi

# End-to-end: call Gemini with a trivial prompt.
if [ "$FAILED" -eq 0 ]; then
    echo
    echo "Calling Gemini to confirm the key works..."
    MODEL="${GEMINI_MODEL:-gemini-3.1-flash-lite}"
    RESPONSE=$(curl -sS -X POST \
        "https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent" \
        -H "x-goog-api-key: ${GOOGLE_API_KEY}" \
        -H "Content-Type: application/json" \
        -d '{"contents":[{"role":"user","parts":[{"text":"Reply with exactly one word: ready"}]}]}' 2>&1)

    if echo "$RESPONSE" | tr '[:upper:]' '[:lower:]' | grep -q "ready"; then
        pass "Gemini call succeeded"
    else
        fail "Gemini call failed. Check your key and network."
        echo "$RESPONSE" | head -20 | sed 's/^/    /'
    fi
fi

echo
if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}All checks passed — you are ready for M8.${NC}"
    exit 0
else
    echo -e "${RED}Some checks failed. Fix the items above and re-run.${NC}"
    exit 1
fi
