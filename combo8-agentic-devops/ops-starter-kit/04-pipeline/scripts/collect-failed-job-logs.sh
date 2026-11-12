#!/usr/bin/env bash
# Collect the logs of this pipeline's failed jobs for the diagnose stage.
#
# Deterministic and read-only: two GET endpoints of the GitLab API, no agent
# involved. Each log is stripped of terminal colour codes, redacted (redact.sh:
# common secret shapes, credentials in URLs and the job's own secret values;
# defence in depth, GitLab already masks masked variables), and cut to its last
# N lines. The log text is still untrusted input: MR authors control what their
# jobs print.
#
# Usage: collect-failed-job-logs.sh [OUT_DIR]          (default: diagnose)
#
# Environment:
#   CI_API_V4_URL, CI_PROJECT_ID, CI_PIPELINE_ID   set by GitLab CI
#   DIAGNOSE_API_TOKEN     project access token, Reporter role, read_api scope is enough here
#   DIAGNOSE_TAIL_LINES    lines kept per job (default 300)
#   DIAGNOSE_MAX_JOBS      failed jobs collected (default 3)
#   DIAGNOSE_REDACT_VARS   extra variable names whose values are redacted (see redact.sh)
#
# Writes:  OUT_DIR/failed-jobs.md and OUT_DIR/<job-name>-<job-id>.log
# Needs:   bash, curl, jq, sed, awk, tail
set -euo pipefail

: "${CI_API_V4_URL:?CI_API_V4_URL is not set}"
: "${CI_PROJECT_ID:?CI_PROJECT_ID is not set}"
: "${CI_PIPELINE_ID:?CI_PIPELINE_ID is not set}"
: "${DIAGNOSE_API_TOKEN:?DIAGNOSE_API_TOKEN is not set}"

out_dir="${1:-diagnose}"
tail_lines="${DIAGNOSE_TAIL_LINES:-300}"
max_jobs="${DIAGNOSE_MAX_JOBS:-3}"

for tool in curl jq sed awk tail; do
  command -v "$tool" >/dev/null 2>&1 || { echo "error: $tool is required" >&2; exit 2; }
done

mkdir -p "$out_dir"
index="$out_dir/failed-jobs.md"

api_get() {
  curl --fail --silent --show-error --max-time 30 \
    --header "PRIVATE-TOKEN: ${DIAGNOSE_API_TOKEN}" \
    "${CI_API_V4_URL}$1"
}

esc=$'\033'
cr=$'\r'
strip_terminal_codes() {
  # colour codes, GitLab collapsible-section markers, carriage returns
  # (portable across GNU, BusyBox and BSD sed: no \r or \n escapes in sed itself)
  sed -E -e "s/${esc}\[[0-9;]*[A-Za-z]//g" \
         -e 's/section_(start|end):[0-9]+:[A-Za-z0-9_.-]+(\[[^]]*\])?//g' \
         -e "s/${cr}\$//" |
    tr '\r' '\n'
}

# redact(): the same pass post-mr-note.sh runs over the diagnosis on the way out.
# shellcheck source-path=SCRIPTDIR
# shellcheck source=redact.sh
. "$(dirname "${BASH_SOURCE[0]}")/redact.sh"

jobs_json="$(api_get "/projects/${CI_PROJECT_ID}/pipelines/${CI_PIPELINE_ID}/jobs?scope%5B%5D=failed&per_page=100")"
failed_count="$(jq 'length' <<<"$jobs_json")"

{
  echo "# Failed jobs in pipeline ${CI_PIPELINE_ID}"
  echo
  if [ "$failed_count" -eq 0 ]; then
    echo "No failed jobs found."
  else
    echo "Collected the last ${tail_lines} lines of up to ${max_jobs} of ${failed_count} failed job(s)."
    echo
    echo "| Job | Stage | Failure reason | Log file | Web URL |"
    echo "|---|---|---|---|---|"
  fi
} >"$index"

jq -r --argjson max "$max_jobs" \
  '.[:$max][] | [(.id|tostring), .name, .stage, (.failure_reason // "unknown"), (.web_url // "")] | @tsv' \
  <<<"$jobs_json" |
while IFS=$'\t' read -r job_id job_name stage reason web_url; do
  safe_name="$(printf '%s' "$job_name" | tr -c 'A-Za-z0-9._-' '_')"
  log_file="${safe_name}-${job_id}.log"
  api_get "/projects/${CI_PROJECT_ID}/jobs/${job_id}/trace" | strip_terminal_codes | redact | tail -n "$tail_lines" >"$out_dir/$log_file"
  echo "| ${job_name} | ${stage} | ${reason} | ${log_file} | ${web_url} |" >>"$index"
done

echo "Wrote $index"
