#!/usr/bin/env bash
#
# Pre-flight check. Run this 48 hours before the workshop.
#
# What it checks:
#   - Node 22+ is available.
#   - Dependencies are installed.
#   - The project typechecks.
#   - The tool tests fail (they should — you haven't written the tools yet)
#     and the reference implementation passes.
#   - A GOOGLE_API_KEY is set (in .env or the environment).
#   - A simple Gemini call succeeds.
#
# If all checks pass, you are ready for M8.

set -u

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

pass() { printf "${GREEN}✅ %s${NC}\n" "$1"; }
fail() { printf "${RED}❌ %s${NC}\n" "$1"; FAILED=1; }
warn() { printf "${YELLOW}⚠️  %s${NC}\n" "$1"; }

FAILED=0

echo "=== Tiny Agent (TypeScript) pre-flight check ==="
echo

# Node version
if command -v node >/dev/null; then
    NODE_VERSION=$(node --version)          # e.g. v22.14.0
    NODE_MAJOR=${NODE_VERSION#v}
    NODE_MAJOR=${NODE_MAJOR%%.*}
    if [ "${NODE_MAJOR:-0}" -ge 22 ] 2>/dev/null; then
        pass "Node $NODE_VERSION (>= 22 required)"
    else
        fail "Node $NODE_VERSION is too old. Install Node 22 or later from https://nodejs.org"
    fi
else
    fail "node not found. Install Node 22 or later from https://nodejs.org"
fi

# Dependencies installed
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

# The reference implementation must pass its own tests.
if [ "$FAILED" -eq 0 ]; then
    if npm run --silent test:reference >/dev/null 2>&1; then
        pass "reference implementation passes all tests"
    else
        fail "reference tests failed — that shouldn't happen. Email workshops@octoco.ai with the output of: npm run test:reference"
    fi
fi

# Your own tests are EXPECTED to fail before the workshop.
if [ "$FAILED" -eq 0 ]; then
    if npm test >/dev/null 2>&1; then
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

# End-to-end: call Gemini with a trivial prompt, through the same SDK the agent uses.
if [ "$FAILED" -eq 0 ]; then
    echo
    echo "Calling Gemini to confirm the key works..."
    # tsx compiles -e snippets as CJS, which forbids top-level await —
    # hence the async IIFE.
    if npx --no-install tsx -e "
import { GoogleGenAI } from '@google/genai';
(async () => {
  const ai = new GoogleGenAI({ apiKey: process.env.GOOGLE_API_KEY });
  const res = await ai.models.generateContent({
    model: process.env.GEMINI_MODEL || 'gemini-3.1-flash-lite',
    contents: 'Reply with exactly one word: ready',
  });
  const text = (res.text ?? '').trim().toLowerCase();
  console.log('Gemini replied:', JSON.stringify(text));
  if (!text.includes('ready')) { throw new Error('unexpected reply: ' + text); }
})();
" 2>&1; then
        pass "Gemini call succeeded"
    else
        fail "Gemini call failed. Check your key and network."
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
