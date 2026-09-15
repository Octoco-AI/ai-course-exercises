#!/usr/bin/env bash
#
# Create a deliberately-regressing branch for the Combo 4 M4 demo.
#
# What it does:
#   - Creates a branch `demo/regression-total-rounding` off the current HEAD.
#   - Rewrites computeTotal() in
#     src/main/java/ai/octoco/legacyservice/Orders.java to round order totals
#     to whole currency units, dressed up as a plausible "POS sync" refactor.
#   - Commits the change.
#
# What it demonstrates:
#   - A PR opened from this branch trips the tests workflow
#     (.github/workflows/tests.yml): LegacyServiceSmokeTests.createOrder_returnsExpectedShape
#     expects total==19.99 and now gets 20.0, so `./mvnw test` fails and the
#     merge is blocked.
#   - Reverting the change turns the PR green again.
#
# Run from the repo root:
#   ./scripts/create-regression-branch.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

TARGET="src/main/java/ai/octoco/legacyservice/Orders.java"

if [ ! -f "$TARGET" ]; then
    echo "Error: run this from the repo root; $TARGET not found." >&2
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

path = Path("src/main/java/ai/octoco/legacyservice/Orders.java")
original = path.read_text()

regressed = original.replace(
    "        double total = subtotal * (1.0 - discountPct / 100.0);\n"
    "        return Utils.money(total);",
    "        double total = subtotal * (1.0 - discountPct / 100.0);\n"
    "        // refactor: round order totals to whole currency units for the POS sync\n"
    "        return (double) Math.round(total);",
)

if regressed == original:
    raise SystemExit("computeTotal block not found -- has Orders.java changed "
                     "since this script was written?")

path.write_text(regressed)
print("Regressed computeTotal() in Orders.java.")
PY

git add "$TARGET"
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
