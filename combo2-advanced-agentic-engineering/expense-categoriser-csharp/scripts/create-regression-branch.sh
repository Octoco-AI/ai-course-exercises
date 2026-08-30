#!/usr/bin/env bash
#
# Create a deliberately-regressing branch for the Combo 2 M12 demo.
#
# What it does:
#   - Creates a branch `demo/regression-prompt` off main.
#   - Tweaks the system prompt in src/ExpenseCategoriser/Core.cs to bias the
#     model toward "Other" for edge cases. This tanks the accuracy metric
#     enough to fail the eval gate.
#   - Commits the change.
#
# What it demonstrates:
#   - A PR opened against main from this branch will trigger evals.yml, which
#     will fail on AccuracyThreshold, which will block the merge.
#   - Fixing the regression (reverting the prompt) turns the PR green again.
#
# Run from the repo root:
#   ./scripts/create-regression-branch.sh
#
# On Windows, run scripts/create-regression-branch.ps1 instead.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

TARGET="src/ExpenseCategoriser/Core.cs"

if [ ! -f "$TARGET" ]; then
    echo "Error: expected to be run from the repo root, with $TARGET present." >&2
    exit 1
fi

BRANCH="demo/regression-prompt"

if git rev-parse --verify "$BRANCH" >/dev/null 2>&1; then
    echo "Branch $BRANCH already exists. Delete it first if you want a fresh demo:"
    echo "    git branch -D $BRANCH"
    exit 1
fi

git checkout -b "$BRANCH"

# Deliberate regression: replace the careful confidence guidance with a bias
# toward "Other"-as-default.
python3 <<'PY'
from pathlib import Path

path = Path("src/ExpenseCategoriser/Core.cs")
original = path.read_text()

regressed = original.replace(
    '''        - "confidence" is your self-reported certainty. Use 0.9+ for obvious matches
          (grocery store -> Food & Dining), 0.5-0.7 for ambiguous cases, below 0.5
          for genuinely unclear items.''',
    '''        - "confidence" is your self-reported certainty. When in doubt, use low
          confidence (0.3-0.5) — it's safer. Prefer the "Other" category for any
          transaction that isn't perfectly obvious.''',
)

if regressed == original:
    raise SystemExit("Prompt block not found — has Core.cs changed since the regression script was written?")

path.write_text(regressed)
print("Regressed Core.cs.")
PY

git add "$TARGET"
git commit -m "demo: regress prompt to bias toward 'Other'

Deliberate regression for Combo 2 M12 demo. Opening a PR against main from
this branch should fail the evals workflow on AccuracyThreshold."

echo
echo "Regression branch ready. Push and open a PR to see evals block the merge:"
echo "    git push -u origin $BRANCH"
echo "    gh pr create --title 'demo: regress the prompt' --body 'Watch me fail the evals.'"
echo
echo "To clean up afterwards:"
echo "    git checkout main"
echo "    git branch -D $BRANCH"
