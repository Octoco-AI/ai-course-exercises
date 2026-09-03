#!/usr/bin/env bash
#
# Create a deliberately-regressing branch for the Combo 4 M4 demo.
#
# What it does:
#   - Creates a branch `demo/regression-total-rounding` off the current HEAD.
#   - Rewrites ComputeTotal() in src/LegacyService/Orders.cs to round order
#     totals to whole currency units, dressed up as a plausible "POS sync"
#     refactor.
#   - Commits the change.
#
# What it demonstrates:
#   - A PR opened from this branch trips the tests workflow (.github/workflows/
#     tests.yml): SmokeTests.CreateOrder_ReturnsExpectedShape expects
#     total==19.99 and now gets 20, so `dotnet test` fails and the merge is
#     blocked.
#   - Reverting the change turns the PR green again.
#
# Run from the repo root:
#   ./scripts/create-regression-branch.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ ! -f src/LegacyService/Orders.cs ]; then
    echo "Error: run this from the repo root; src/LegacyService/Orders.cs not found." >&2
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
# Uses a python3 heredoc for the exact-block replace, matching the house
# convention in examples/csharp/expense-categoriser-csharp -- python3 is
# already a prerequisite on the C# path for M10.
python3 <<'PY'
from pathlib import Path

path = Path("src/LegacyService/Orders.cs")
original = path.read_text()

regressed = original.replace(
    "        var total = subtotal * (1.0 - discountPct / 100.0);\n"
    "        return Utils.Money(total);",
    "        var total = subtotal * (1.0 - discountPct / 100.0);\n"
    "        // refactor: round order totals to whole currency units for the POS sync\n"
    "        return Math.Round(total);",
)

if regressed == original:
    raise SystemExit("ComputeTotal block not found -- has Orders.cs changed "
                     "since this script was written?")

path.write_text(regressed)
print("Regressed ComputeTotal() in Orders.cs.")
PY

git add src/LegacyService/Orders.cs
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
