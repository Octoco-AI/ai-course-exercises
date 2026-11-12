#!/usr/bin/env bash
# Read-only Argo CD sync and drift report (m64).
#
# Lists applications, reads their sync and health status, and diffs each one's
# live state against Git. It only ever calls `argocd app list`, `argocd app get`
# and `argocd app diff`, and refuses any other verb (see argocd_ro). It never
# syncs, refreshes, rolls back, sets or deletes.
#
# Usage:
#   argo-drift-check.sh [-p PROJECT] [-l SELECTOR] [-o REPORT.md] [-n MAX_DIFF_LINES]
#
#   -p PROJECT        only applications in this Argo CD project
#   -l SELECTOR       only applications matching this label selector, e.g. team=orders
#   -o REPORT.md      write the Markdown report here (default: stdout)
#   -n LINES          diff lines to include per drifted application (default 40)
#
# Environment:
#   ARGOCD_SERVER       Argo CD API address, e.g. argocd.example.internal   (required)
#   ARGOCD_AUTH_TOKEN   token for a read-only Argo CD account; read by the CLI from the
#                       environment, so it never appears on a command line
#   ARGOCD_API_TOKEN    the same token under the name the argocd-mcp server reads
#                       (01-access/mcp/). Used when ARGOCD_AUTH_TOKEN is unset, so
#                       one read-only token serves both.        (one of the two required)
#   ARGOCD_GRPC_WEB     set to "true" if the server sits behind a proxy without HTTP/2
#
# Exit codes (mirroring `argocd app diff`):
#   0  no drift    1  drift or OutOfSync found    2  error (bad usage, CLI or API failure)
#
# Needs: argocd CLI, jq.
set -euo pipefail

project=""
selector=""
report=""
max_diff_lines=40

usage() { sed -n '2,/^set -euo/p' "$0" | sed -e '$d' -e 's/^# \{0,1\}//'; }
die() { echo "error: $*" >&2; exit 2; }

while getopts ":p:l:o:n:h" opt; do
  case "$opt" in
    p) project="$OPTARG" ;;
    l) selector="$OPTARG" ;;
    o) report="$OPTARG" ;;
    n) max_diff_lines="$OPTARG" ;;
    h) usage; exit 0 ;;
    :) die "option -$OPTARG needs a value" ;;
    *) die "unknown option -$OPTARG (try -h)" ;;
  esac
done
shift $((OPTIND - 1))
[ "$#" -eq 0 ] || die "unexpected argument: $1"
[[ "$max_diff_lines" =~ ^[0-9]+$ ]] || die "-n must be a number"

: "${ARGOCD_SERVER:?ARGOCD_SERVER is not set}"
if [ -z "${ARGOCD_AUTH_TOKEN:-}" ] && [ -n "${ARGOCD_API_TOKEN:-}" ]; then
  export ARGOCD_AUTH_TOKEN="$ARGOCD_API_TOKEN"
fi
: "${ARGOCD_AUTH_TOKEN:?ARGOCD_AUTH_TOKEN (or ARGOCD_API_TOKEN) is not set}"
command -v argocd >/dev/null 2>&1 || die "argocd CLI not found"
command -v jq >/dev/null 2>&1 || die "jq not found"

global_flags=(--server "$ARGOCD_SERVER")
if [ "${ARGOCD_GRPC_WEB:-}" = "true" ]; then
  global_flags+=(--grpc-web)
fi

# The only door to the argocd CLI. Anything but app list/get/diff is refused.
argocd_ro() {
  case "${1:-} ${2:-}" in
    "app list" | "app get" | "app diff") ;;
    *) echo "refused: argocd $* is not a read-only verb" >&2; return 2 ;;
  esac
  argocd "$@" "${global_flags[@]}"
}

list_args=(app list -o json)
[ -n "$project" ] && list_args+=(-p "$project")
[ -n "$selector" ] && list_args+=(-l "$selector")

apps_json="$(argocd_ro "${list_args[@]}")" || die "argocd app list failed"
jq -e 'type == "array"' >/dev/null <<<"$apps_json" || die "unexpected output from argocd app list"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

drifted=0
errors=0
rows="$tmp/rows.md"
details="$tmp/details.md"
: >"$rows"
: >"$details"

while IFS=$'\t' read -r app sync health; do
  [ -n "$app" ] || continue
  set +e
  argocd_ro app diff "$app" >"$tmp/diff.txt" 2>"$tmp/diff.err"
  rc=$?
  set -e
  case "$rc" in
    0) drift="no" ;;
    1)
      drift="yes"
      drifted=$((drifted + 1))
      {
        echo "### $app"
        echo
        echo '```diff'
        head -n "$max_diff_lines" "$tmp/diff.txt"
        total_lines="$(wc -l <"$tmp/diff.txt" | tr -d ' ')"
        if [ "$total_lines" -gt "$max_diff_lines" ]; then
          echo "... ($((total_lines - max_diff_lines)) more lines; run: argocd app diff $app)"
        fi
        echo '```'
        echo
      } >>"$details"
      ;;
    *)
      drift="error"
      errors=$((errors + 1))
      {
        echo "### $app — diff failed (exit $rc)"
        echo
        echo '```'
        head -n 10 "$tmp/diff.err"
        echo '```'
        echo
      } >>"$details"
      ;;
  esac
  if [ "$sync" != "Synced" ] && [ "$drift" = "no" ]; then
    drifted=$((drifted + 1))
  fi
  echo "| $app | $sync | $health | $drift |" >>"$rows"
done < <(jq -r '.[] | [.metadata.name, (.status.sync.status // "Unknown"), (.status.health.status // "Unknown")] | @tsv' <<<"$apps_json")

app_count="$(jq 'length' <<<"$apps_json")"

emit() {
  echo "# Argo CD drift report"
  echo
  echo "Server: \`$ARGOCD_SERVER\`  Project: \`${project:-all}\`  Selector: \`${selector:-none}\`  Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
  echo "Applications: $app_count  Drifted or out of sync: $drifted  Errors: $errors"
  echo
  if [ "$app_count" -gt 0 ]; then
    echo "| Application | Sync | Health | Live differs from Git |"
    echo "|---|---|---|---|"
    cat "$rows"
    echo
  fi
  if [ -s "$details" ]; then
    echo "## Details"
    echo
    cat "$details"
  fi
  echo "_Read-only check. Nothing was synced, refreshed or changed. Decide on any sync in a reviewed MR or with a human-approved sync._"
}

if [ -n "$report" ]; then
  emit >"$report"
else
  emit
fi

if [ "$errors" -gt 0 ]; then
  exit 2
elif [ "$drifted" -gt 0 ]; then
  exit 1
fi
exit 0
