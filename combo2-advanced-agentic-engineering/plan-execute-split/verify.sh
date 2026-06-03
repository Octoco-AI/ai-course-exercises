#!/usr/bin/env bash
#
# Pre-flight check. Run this before the workshop (5 minutes).
#
# What it checks:
#   - Python 3.12+ is available.
#   - `google-genai` and `python-dotenv` are installed.
#   - A GOOGLE_API_KEY is set (in .env or the environment).
#   - The WORKSPACE directory exists.
#   - A simple Gemini call succeeds.
#
# If all checks pass, you are ready for M7.

set -u

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

pass() { printf "${GREEN}✅ %s${NC}\n" "$1"; }
fail() { printf "${RED}❌ %s${NC}\n" "$1"; FAILED=1; }
warn() { printf "${YELLOW}⚠️  %s${NC}\n" "$1"; }

FAILED=0

echo "=== Plan/execute split pre-flight check ==="
echo

# Python version
if command -v python3 >/dev/null; then
    PY_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    PY_MINOR=$(python3 -c 'import sys; print(sys.version_info[1])')
    if [ "$PY_MINOR" -ge 12 ]; then
        pass "Python $PY_VERSION (>= 3.12 required)"
    else
        fail "Python $PY_VERSION is too old. Install Python 3.12 or later."
    fi
else
    fail "python3 not found. Install Python 3.12 or later."
fi

# Dependencies
if python3 -c 'import google.genai' 2>/dev/null; then
    pass "google-genai installed"
else
    fail "google-genai not installed. Run: pip install google-genai python-dotenv"
fi
if python3 -c 'import dotenv' 2>/dev/null; then
    pass "python-dotenv installed"
else
    fail "python-dotenv not installed. Run: pip install google-genai python-dotenv"
fi

# Load .env
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
fi

# API key
if [ -n "${GOOGLE_API_KEY:-}" ] && [ "${GOOGLE_API_KEY}" != "your_gemini_api_key_here" ]; then
    pass "GOOGLE_API_KEY is set"
else
    fail "GOOGLE_API_KEY not set. Copy .env.example to .env and add your key (https://aistudio.google.com/apikey)"
fi

# Workspace
WS="${WORKSPACE:-../expense-categoriser}"
if [ -d "$WS" ]; then
    pass "WORKSPACE exists: $WS"
else
    warn "WORKSPACE '$WS' not found. Set WORKSPACE in .env to a repo the agent can edit."
fi

# End-to-end Gemini call
if [ "$FAILED" -eq 0 ]; then
    echo
    echo "Calling Gemini to confirm the key works..."
    if python3 -c "
import os
from google import genai
client = genai.Client(api_key=os.environ['GOOGLE_API_KEY'])
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='Reply with exactly one word: ready'
)
text = (response.text or '').strip().lower()
print(f'Gemini replied: {text!r}')
assert 'ready' in text, f'unexpected reply: {text!r}'
" 2>&1; then
        pass "Gemini call succeeded"
    else
        fail "Gemini call failed. Check your key and network."
    fi
fi

echo
if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}All checks passed — you are ready for M7.${NC}"
    exit 0
else
    echo -e "${RED}Some checks failed. Fix the items above and re-run.${NC}"
    exit 1
fi
