#!/usr/bin/env bash
#
# Copy the chroma-corpora Track A docs into workspace/ so the agent has
# something to read and draft patches against. Safe to run repeatedly.

set -eu

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$REPO_ROOT/../chroma-corpora/track-a-codebase/docs"
DEST="$REPO_ROOT/workspace"

if [ ! -d "$SOURCE" ]; then
    echo "Error: source docs not found at $SOURCE." >&2
    echo "Make sure ../chroma-corpora is checked out at the expected path." >&2
    exit 1
fi

mkdir -p "$DEST"

# Clean (but keep .gitkeep so the dir is never "missing")
find "$DEST" -mindepth 1 -name ".gitkeep" -prune -o -exec rm -rf {} + 2>/dev/null || true

# Copy the docs over. Preserve structure so search_docs and read_file refer
# to the same paths.
cp -r "$SOURCE"/* "$DEST/"

echo "✅ Workspace seeded from $SOURCE"
ls -1 "$DEST"
