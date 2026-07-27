#!/usr/bin/env bash
#
# Copy the chroma-corpora Track B KB articles into workspace/. Safe to re-run.

set -eu

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$REPO_ROOT/../chroma-corpora/track-b-helpdesk/docs"
DEST="$REPO_ROOT/workspace"

if [ ! -d "$SOURCE" ]; then
    echo "Error: source docs not found at $SOURCE." >&2
    exit 1
fi

mkdir -p "$DEST"
find "$DEST" -mindepth 1 -name ".gitkeep" -prune -o -exec rm -rf {} + 2>/dev/null || true
cp -r "$SOURCE"/* "$DEST/"

echo "✅ Workspace seeded from $SOURCE"
ls -1 "$DEST"
