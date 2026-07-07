#!/usr/bin/env bash
#
# Create a deliberately-regressing branch for the Combo 4 M4 demo.
#
# What it does:
#   - Creates a branch `demo/regression-total-rounding` off the current HEAD.
#   - Rewrites compute_total() in src/legacy_service/orders.py to round order
#     totals to whole currency units, dressed up as a plausible "POS sync"
#     refactor.
#   - Commits the change.
#
# What it demonstrates:
#   - A PR opened from this branch trips the tests workflow (.github/workflows/
#     tests.yml): tests/test_smoke.py::test_create_order expects total==19.99
#     and now gets 20.0, so pytest fails and the merge is blocked.
#   - Reverting the change turns the PR green again.
#
# Run from the repo root:
#   ./scripts/create-regression-branch.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ ! -f src/legacy_service/orders.py ]; then
    echo "Error: run this from the repo root; src/legacy_service/orders.py not found." >&2
    exit 1
fi

BRANCH="demo/regression-total-rounding"

if git rev-parse --verify "$BRANCH" >/dev/null 2>&1; then
    echo "Branch $BRANCH already exists. Delete it first if you want a fresh demo:"
    echo "    git branch -D $BRANCH"
    exit 1
fi

git checkout -b "$BRANCH"

# Deliberate regression: round totals to whole units instead of to cents.
python3 <<'PY'
from pathlib import Path

path = Path("src/legacy_service/orders.py")
original = path.read_text()

regressed = original.replace(
    "    total = subtotal * (1.0 - discount_pct / 100.0)\n"
    "    return money(total)",
    "    total = subtotal * (1.0 - discount_pct / 100.0)\n"
    "    # refactor: round order totals to whole currency units for the POS sync\n"
    "    return round(total)",
)

if regressed == original:
    raise SystemExit("compute_total block not found -- has orders.py changed "
                     "since this script was written?")

path.write_text(regressed)
print("Regressed compute_total() in orders.py.")
PY

git add src/legacy_service/orders.py
git commit -m "refactor: round order totals to whole units for POS sync

Deliberate regression for the Combo 4 M4 demo. Opening a PR from this branch
should fail the tests workflow: the smoke suite expects cent-accurate totals."

echo
echo "Regression branch ready. Push and open a PR to see CI block the merge:"
echo "    git push -u origin $BRANCH"
echo "    gh pr create --title 'refactor: whole-unit order totals' --body 'Watch me fail CI.'"
echo
echo "To clean up afterwards:"
echo "    git checkout -"
echo "    git branch -D $BRANCH"
