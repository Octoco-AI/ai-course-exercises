#!/usr/bin/env bash
#
# Pre-flight install + import verification for the four eval / observability
# tools used across Combo 2 and Combo 3.
#
# Usage:
#   ./_shared/verify-eval-tools.sh              # check current venv
#   ./_shared/verify-eval-tools.sh --fresh      # create a fresh venv at ./.eval-tools-venv/
#                                                and run the full install + check there
#
# What it does:
#   1. (--fresh only) creates a new venv.
#   2. Installs deepeval, inspect-ai, opik, chromadb.
#   3. Verifies each imports without error.
#   4. Runs a trivial Chroma query to warm the embedding-model cache.
#   5. Reports installed versions.
#
# Full runbook with friction notes: eval-tooling-install.md

set -u

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

pass() { printf "${GREEN}✅ %s${NC}\n" "$1"; }
fail() { printf "${RED}❌ %s${NC}\n" "$1"; FAILED=1; }
warn() { printf "${YELLOW}⚠️  %s${NC}\n" "$1"; }

FAILED=0
FRESH=0

for arg in "$@"; do
  case "$arg" in
    --fresh) FRESH=1 ;;
    -h|--help)
      sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
  esac
done

if [ "$FRESH" -eq 1 ]; then
  VENV_PATH="$(pwd)/.eval-tools-venv"
  echo "=== Creating fresh venv at $VENV_PATH ==="
  rm -rf "$VENV_PATH"
  python3 -m venv "$VENV_PATH"
  # shellcheck source=/dev/null
  . "$VENV_PATH/bin/activate"
  pip install --upgrade pip --quiet
fi

echo "=== Python version ==="
python3 --version
echo

# Install in the recommended order. Quiet unless something fails.
for pkg in chromadb opik deepeval inspect-ai; do
  echo "=== Installing $pkg ==="
  if pip install --quiet "$pkg" 2>&1 | grep -v "^$" | tail -3; then
    :
  fi
  VERSION=$(python3 -c "import importlib.metadata as m; print(m.version('$pkg'))" 2>/dev/null || echo "unknown")
  pass "$pkg $VERSION installed"
  echo
done

echo "=== Import check ==="
python3 <<'PY'
import sys
failed = []

for mod in ("deepeval", "inspect_ai", "opik", "chromadb"):
    try:
        __import__(mod)
        print(f"  ✅ {mod}")
    except Exception as e:
        print(f"  ❌ {mod}: {e}")
        failed.append(mod)

sys.exit(1 if failed else 0)
PY
if [ $? -ne 0 ]; then
    fail "one or more imports failed"
fi
echo

echo "=== Chroma cache warm-up (downloads ~79MB ONNX model on first run) ==="
python3 <<'PY'
import chromadb
c = chromadb.Client()
col = c.get_or_create_collection("verify")
col.add(documents=["workshop test document"], ids=["1"])
result = col.query(query_texts=["workshop"], n_results=1)
assert result["ids"][0][0] == "1", f"unexpected result: {result}"
print("  Chroma query OK — embedding cache is now warm at ~/.cache/chroma/")
PY
if [ $? -ne 0 ]; then
    fail "Chroma smoke test failed"
fi
echo

echo "=== Summary ==="
python3 <<'PY'
import importlib.metadata as m
for pkg in ("deepeval", "inspect-ai", "opik", "chromadb"):
    try:
        print(f"  {pkg:15s} {m.version(pkg)}")
    except Exception:
        print(f"  {pkg:15s} (not installed)")
PY
echo

if [ "$FAILED" -eq 0 ]; then
  echo -e "${GREEN}All tools ready.${NC}"
  if [ "$FRESH" -eq 1 ]; then
    echo "Fresh venv is at .eval-tools-venv/ — activate with: source .eval-tools-venv/bin/activate"
  fi
  exit 0
else
  echo -e "${RED}Some checks failed. See eval-tooling-install.md Friction findings.${NC}"
  exit 1
fi
