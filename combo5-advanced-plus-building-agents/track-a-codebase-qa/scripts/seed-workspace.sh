#!/usr/bin/env bash
#
# Copy the chroma-corpora Track A docs into workspace/ so the agent has
# something to read and draft patches against, plus the small buggy code
# module M11's "find and fix the bug" prompt targets. Safe to run repeatedly.

set -eu

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCS_SOURCE="$REPO_ROOT/../chroma-corpora/track-a-codebase/docs"
CODE_SOURCE="$REPO_ROOT/sample_code"
DEST="$REPO_ROOT/workspace"

if [ ! -d "$DOCS_SOURCE" ]; then
    echo "Error: source docs not found at $DOCS_SOURCE." >&2
    echo "Make sure ../chroma-corpora is checked out at the expected path." >&2
    exit 1
fi

mkdir -p "$DEST"

# Clean (but keep .gitkeep so the dir is never "missing")
find "$DEST" -mindepth 1 -name ".gitkeep" -prune -o -exec rm -rf {} + 2>/dev/null || true

# Copy the docs over. Preserve structure so search_docs (Module 13) and
# read_file keep referring to the same paths (docs stay flat at the
# workspace root — the Chroma corpus's `source` metadata is a bare filename).
cp -r "$DOCS_SOURCE"/* "$DEST/"

# Copy the buggy code module into workspace/src/ — this is what
# "Find and fix the bug in src/math_utils.py" (Module 11, Step 7) targets.
mkdir -p "$DEST/src"
cp -r "$CODE_SOURCE"/* "$DEST/src/"

echo "✅ Workspace seeded from $DOCS_SOURCE + $CODE_SOURCE"
ls -1 "$DEST"
