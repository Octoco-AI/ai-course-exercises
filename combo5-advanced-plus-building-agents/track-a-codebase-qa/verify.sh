#!/usr/bin/env bash
#
# Pre-flight check for the Track A running artefact.

set -u

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

pass() { printf "${GREEN}✅ %s${NC}\n" "$1"; }
fail() { printf "${RED}❌ %s${NC}\n" "$1"; FAILED=1; }
warn() { printf "${YELLOW}⚠️  %s${NC}\n" "$1"; }

FAILED=0

echo "=== Track A — Codebase Q&A pre-flight ==="
echo

# Python 3.12+
if command -v python3 >/dev/null; then
    PY_V=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    PY_MINOR=$(python3 -c 'import sys; print(sys.version_info[1])')
    PY_MAJOR=$(python3 -c 'import sys; print(sys.version_info[0])')
    if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 12 ]; then
        pass "Python $PY_V"
    else
        fail "Python $PY_V too old (need 3.12+)"
    fi
else
    fail "python3 not found"
fi

# Core imports (google.genai is the default provider; anthropic is the alternative)
for mod in google.genai anthropic fastapi uvicorn chromadb; do
    if python3 -c "import $mod" 2>/dev/null; then
        pass "$mod installed"
    else
        fail "$mod not installed. Run: pip install -e '.[dev]'"
    fi
done

# .env
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
fi

if [ -n "${GOOGLE_API_KEY:-}" ] && [ "$GOOGLE_API_KEY" != "your_gemini_api_key_here" ]; then
    pass "GOOGLE_API_KEY set (Gemini — default provider)"
elif [ -n "${ANTHROPIC_API_KEY:-}" ] && [ "$ANTHROPIC_API_KEY" != "your_anthropic_api_key_here" ]; then
    pass "ANTHROPIC_API_KEY set (Anthropic — alternative provider)"
else
    warn "No LLM key set — set GOOGLE_API_KEY (default) or ANTHROPIC_API_KEY (alt). Backend fails at runtime; unit tests still run."
fi

# Workspace
if [ -d workspace ] && [ "$(ls -A workspace 2>/dev/null | grep -v '^\.gitkeep$' | wc -l)" -gt 0 ]; then
    pass "workspace/ populated"
else
    warn "workspace/ is empty. Run ./scripts/seed-workspace.sh to seed it."
fi

# Chroma index — not needed until Module 13 (search_docs), but Module 13's
# prep step has you build it early alongside everything else.
CHROMA_DIR="../chroma-corpora/track-a-codebase/.chroma"
if [ -d "$CHROMA_DIR" ]; then
    pass "Track A Chroma index present"
else
    warn "Chroma index missing at $CHROMA_DIR (not needed until Module 13). Build it: (cd ../chroma-corpora/track-a-codebase && python build.py)"
fi

# Unit tests. Module 11/12 tests are designed to SKIP (not fail) until
# you've implemented the step they check — a fresh starter is green here.
echo
echo "=== Running tests ==="
if pytest -v 2>&1 | tail -40; then
    if [ "${PIPESTATUS[0]}" -eq 0 ]; then
        pass "all tests pass (or skip pending your implementation)"
    else
        fail "some tests failed"
    fi
fi
echo
echo "Check your Module 11 work specifically:  pytest -m m11"
echo "Check your Module 12 work specifically:  pytest -m m12"
echo "Check your Module 13 work specifically:  pytest -m m13"
echo "Fell behind? Catch up to a module's end state: ./scripts/checkpoint.sh m11-end"

# Optional: UI build sanity
if [ -d ui/node_modules ]; then
    pass "UI deps installed (run 'npm run build' in ui/ to compile the static bundle)"
else
    warn "UI deps not installed yet. Run: cd ui && npm install"
fi

echo
if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}Ready.${NC}"
    echo "Start the backend: track-a-server  (or: uvicorn backend.server:app --reload)"
    echo "Build + run in Docker: docker compose up --build"
    exit 0
else
    echo -e "${RED}Some checks failed.${NC}"
    exit 1
fi
