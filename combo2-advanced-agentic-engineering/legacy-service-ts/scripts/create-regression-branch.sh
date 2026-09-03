#!/usr/bin/env bash
#
# Create a deliberately-regressing branch for the Combo 4 M4 demo.
#
# What it does:
#   - Creates a branch `demo/regression-total-rounding` off the current HEAD.
#   - Rewrites computeTotal() in src/orders.ts to round order totals to whole
#     currency units, dressed up as a plausible "POS sync" refactor.
#   - Commits the change.
#
# What it demonstrates:
#   - A PR opened from this branch trips the tests workflow (.github/workflows/
#     tests.yml): the "creates an order" smoke test expects total===19.99 and
#     now gets 20, so `npm test` fails and the merge is blocked.
#   - Reverting the change turns the PR green again.
#
# Run from the repo root:
#   ./scripts/create-regression-branch.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

TARGET="src/orders.ts"

if [ ! -f "$TARGET" ]; then
    echo "Error: expected to be run from the repo root, with $TARGET present." >&2
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
node --input-type=module <<'JS'
import { readFileSync, writeFileSync } from "node:fs";

const path = "src/orders.ts";
const original = readFileSync(path, "utf8");

const before = `  const total = subtotal * (1 - discountPct / 100);
  return money(total);`;

const after = `  const total = subtotal * (1 - discountPct / 100);
  // refactor: round order totals to whole currency units for the POS sync
  return Math.round(total);`;

const regressed = original.replace(before, after);

if (regressed === original) {
  console.error("computeTotal block not found -- has orders.ts changed since the regression script was written?");
  process.exit(1);
}

writeFileSync(path, regressed);
console.log("Regressed computeTotal() in orders.ts.");
JS

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
