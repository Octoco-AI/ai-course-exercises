#!/usr/bin/env bash
#
# Pre-flight check for the chroma-corpora sample.
#
# Usage:
#   ./verify.sh               # sanity check + build both indexes
#   ./verify.sh --tests-only  # only run unit tests, skip index build

set -u

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

pass() { printf "${GREEN}✅ %s${NC}\n" "$1"; }
fail() { printf "${RED}❌ %s${NC}\n" "$1"; FAILED=1; }
warn() { printf "${YELLOW}⚠️  %s${NC}\n" "$1"; }

FAILED=0
TESTS_ONLY=0
for arg in "$@"; do
    case "$arg" in
        --tests-only) TESTS_ONLY=1 ;;
    esac
done

echo "=== chroma-corpora pre-flight ==="
echo

# Python
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

# chromadb
if python3 -c 'import chromadb' 2>/dev/null; then
    CHROMA_VERSION=$(python3 -c 'import importlib.metadata as m; print(m.version("chromadb"))')
    pass "chromadb $CHROMA_VERSION"
else
    fail "chromadb not installed. Run: pip install -e '.[dev]'"
fi

# Shared module imports
if python3 -c 'from shared.indexer import build_index; from shared.search import CorpusSearch' 2>/dev/null; then
    pass "shared.indexer and shared.search import"
else
    fail "shared module import failed"
fi

# Unit tests
echo
echo "=== Running unit tests ==="
if pytest -v tests/ 2>&1 | tail -20; then
    if [ "${PIPESTATUS[0]}" -eq 0 ]; then
        pass "unit tests pass"
    else
        fail "unit tests failed"
    fi
fi

if [ "$TESTS_ONLY" -eq 1 ]; then
    echo
    if [ "$FAILED" -eq 0 ]; then
        echo -e "${GREEN}Unit tests green.${NC}"
        exit 0
    else
        exit 1
    fi
fi

# Build both indexes
echo
echo "=== Building Track A (TodoMagic) index ==="
(cd track-a-codebase && python3 build.py) && pass "Track A built" || fail "Track A build failed"

echo
echo "=== Building Track B (Streakly helpdesk) index ==="
(cd track-b-helpdesk && python3 build.py) && pass "Track B built" || fail "Track B build failed"

# Quick search against each
echo
echo "=== Sanity search: Track A ==="
(cd track-a-codebase && python3 search_example.py "how do I run the tests") || fail "Track A search failed"

echo
echo "=== Sanity search: Track B ==="
(cd track-b-helpdesk && python3 search_example.py "how do I enable 2FA") || fail "Track B search failed"

echo
if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}All checks passed.${NC}"
    echo "Indexes persisted to:"
    echo "   track-a-codebase/.chroma/"
    echo "   track-b-helpdesk/.chroma/"
    exit 0
else
    echo -e "${RED}Some checks failed.${NC}"
    exit 1
fi
