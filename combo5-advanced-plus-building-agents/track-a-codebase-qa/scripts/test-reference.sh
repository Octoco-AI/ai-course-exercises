#!/usr/bin/env bash
#
# Facilitator-only. Runs the full test suite against reference/ (the
# Module 12 end-state worked implementation) instead of whatever's
# currently in backend/ui — useful for rehearsing before a cohort, or
# confirming the reference itself is still green after an SDK bump.
#
# Requires a clean git working tree in backend/ and ui/src/ (it restores
# via `git checkout` on exit) — run this in your own clone, not an
# attendee's.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ -n "$(git status --porcelain backend/ ui/src/hooks/useStreamingChat.ts ui/src/components/ToolCallBlock.tsx 2>/dev/null)" ]; then
    echo "backend/ or the M12 UI files have uncommitted changes. Commit or stash first." >&2
    exit 1
fi

cleanup() {
    echo "Restoring backend/ and the M12 UI files from git..."
    git checkout -- backend/ ui/src/hooks/useStreamingChat.ts ui/src/components/ToolCallBlock.tsx 2>/dev/null || true
}
trap cleanup EXIT

echo "Overlaying reference/ onto backend/ and ui/src/ ..."
cp -r reference/backend/. backend/
cp reference/ui/src/hooks/useStreamingChat.ts ui/src/hooks/useStreamingChat.ts
cp reference/ui/src/components/ToolCallBlock.tsx ui/src/components/ToolCallBlock.tsx

echo "=== Running full test suite against the reference implementation ==="
pytest -v
