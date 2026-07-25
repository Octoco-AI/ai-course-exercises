#!/usr/bin/env bash
#
# Pre-flight check for the expense-categoriser sample repo.
#
# Usage:
#   ./verify.sh            # check and run fast (unit) tests
#   ./verify.sh --evals    # also run the eval suite (requires GOOGLE_API_KEY)

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
    esac
done

echo "=== Expense Categoriser pre-flight ==="
echo

# Python 3.12+
if command -v python3 >/dev/null; then
    PY_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    PY_MINOR=$(python3 -c 'import sys; print(sys.version_info[1])')
    PY_MAJOR=$(python3 -c 'import sys; print(sys.version_info[0])')
    if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 12 ]; then
        pass "Python $PY_VERSION"
    else
        fail "Python $PY_VERSION is too old (need 3.12+)"
    fi
else
    fail "python3 not found"
fi

# Dependencies
for pkg in fastapi uvicorn google.genai pydantic pytest; do
    # Map dotted names to module names
    MOD="$pkg"
    if python3 -c "import $MOD" 2>/dev/null; then
        pass "$pkg importable"
    else
        fail "$pkg not importable. Run: pip install -e '.[dev]'"
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
    pass "GOOGLE_API_KEY is set"
    KEY_SET=1
else
    warn "GOOGLE_API_KEY not set — unit tests will still pass, evals will be skipped"
    KEY_SET=0
fi

# Run unit + API tests (no key needed — LLM is mocked)
echo
echo "=== Running unit + API tests (no API key needed) ==="
if pytest -v -m "not evals" 2>&1 | tail -30; then
    if [ "${PIPESTATUS[0]}" -eq 0 ]; then
        pass "unit + API tests pass"
    else
        fail "unit + API tests failed"
    fi
fi

# Optionally run evals
if [ "$RUN_EVALS" -eq 1 ]; then
    if [ "$KEY_SET" -ne 1 ]; then
        fail "cannot run --evals without GOOGLE_API_KEY"
    else
        echo
        echo "=== Running eval suite (calls Gemini — takes ~30s) ==="
        if pytest -v -s -m evals tests/evals/ 2>&1 | tail -40; then
            if [ "${PIPESTATUS[0]}" -eq 0 ]; then
                pass "eval suite passes"
            else
                fail "eval suite failed — see output above for which gate"
            fi
        fi
    fi
fi

echo
if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}Ready. Start the API with: expense-api${NC}"
    exit 0
else
    echo -e "${RED}Some checks failed.${NC}"
    exit 1
fi
