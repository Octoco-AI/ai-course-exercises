#!/usr/bin/env bash
#
# Copy the chroma-corpora Track B KB articles into workspace/, plus the
# sample support tickets M11's ticket-handling tools operate on. Safe to
# re-run.

set -eu

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCS_SOURCE="$REPO_ROOT/../chroma-corpora/track-b-helpdesk/docs"
TICKETS_SOURCE="$REPO_ROOT/sample_tickets"
DEST="$REPO_ROOT/workspace"

if [ ! -d "$DOCS_SOURCE" ]; then
    echo "Error: source docs not found at $DOCS_SOURCE." >&2
    exit 1
fi

mkdir -p "$DEST"
find "$DEST" -mindepth 1 -name ".gitkeep" -prune -o -exec rm -rf {} + 2>/dev/null || true

# KB articles stay flat at the workspace root — search_kb's (Module 13)
# Chroma corpus `source` metadata is a bare filename and must keep
# matching read_article(path).
cp -r "$DOCS_SOURCE"/* "$DEST/"

# Sample tickets — what list_tickets() / read_ticket() / draft_reply()
# (Module 11) operate on.
mkdir -p "$DEST/tickets"
cp -r "$TICKETS_SOURCE"/* "$DEST/tickets/"

echo "✅ Workspace seeded from $DOCS_SOURCE + $TICKETS_SOURCE"
ls -1 "$DEST"
