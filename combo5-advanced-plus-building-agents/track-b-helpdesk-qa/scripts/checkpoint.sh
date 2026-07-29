#!/usr/bin/env bash
#
# Apply a catch-up checkpoint over the live backend/ui tree — for a pair
# that fell behind and wants to rejoin at the next module's starting point.
#
# Usage:
#   ./scripts/checkpoint.sh m11-end   # sets you up to start Module 12
#   ./scripts/checkpoint.sh m12-end   # sets you up to start Module 13
#
# This OVERWRITES the files the checkpoint provides (only those files —
# everything else in backend/ and ui/ is left alone). If you have work you
# want to keep, commit or stash it first.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
name="${1:-}"

if [ -z "$name" ]; then
    echo "Usage: $0 <checkpoint-name>  (e.g. m11-end, m12-end)" >&2
    echo "Available checkpoints:" >&2
    ls -1 "$REPO_ROOT/checkpoints" >&2
    exit 1
fi

SRC="$REPO_ROOT/checkpoints/$name"
if [ ! -d "$SRC" ]; then
    echo "No such checkpoint: $name" >&2
    echo "Available checkpoints:" >&2
    ls -1 "$REPO_ROOT/checkpoints" >&2
    exit 1
fi

echo "Applying checkpoint '$name' over $REPO_ROOT ..."
cp -r "$SRC"/. "$REPO_ROOT"/
echo "✅ Applied. Re-run ./verify.sh, or the module's pytest marker, to confirm."
