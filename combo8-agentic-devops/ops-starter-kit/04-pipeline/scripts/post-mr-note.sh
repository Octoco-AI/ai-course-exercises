#!/usr/bin/env bash
# Post the agent's diagnosis as a comment on the merge request.
#
# Deterministic: the agent writes a file; this script, not the agent, talks to
# the GitLab API. The agent in the diagnose job has no network or shell tools.
#
# The diagnosis is untrusted output: the agent read logs an MR author can
# influence. Before posting, it gets the same redaction pass as the logs
# (redact.sh), over the whole file and before truncation, so a cut cannot
# split a secret past the patterns.
#
# Usage: post-mr-note.sh DIAGNOSIS_FILE
#
# Environment:
#   CI_API_V4_URL, CI_PROJECT_ID, CI_PIPELINE_URL   set by GitLab CI
#   CI_MERGE_REQUEST_IID   set in merge request pipelines; without it, nothing is posted
#   DIAGNOSE_API_TOKEN     project access token, Reporter role, api scope (needed to comment)
#   DIAGNOSE_NOTE_MAX_BYTES  cap on the comment body (default 60000)
#   DIAGNOSE_REDACT_VARS   extra variable names whose values are redacted (see redact.sh)
set -euo pipefail

# shellcheck source-path=SCRIPTDIR
# shellcheck source=redact.sh
. "$(dirname "${BASH_SOURCE[0]}")/redact.sh"

diagnosis="${1:?usage: post-mr-note.sh DIAGNOSIS_FILE}"
: "${CI_API_V4_URL:?CI_API_V4_URL is not set}"
: "${CI_PROJECT_ID:?CI_PROJECT_ID is not set}"
: "${DIAGNOSE_API_TOKEN:?DIAGNOSE_API_TOKEN is not set}"
max_bytes="${DIAGNOSE_NOTE_MAX_BYTES:-60000}"

if [ -z "${CI_MERGE_REQUEST_IID:-}" ]; then
  echo "Not a merge request pipeline; the diagnosis stays in the job artefacts."
  exit 0
fi

if [ ! -s "$diagnosis" ]; then
  echo "error: $diagnosis is missing or empty; nothing to post" >&2
  exit 1
fi

body="$(mktemp)"
clean="$(mktemp)"
trap 'rm -f "$body" "$clean"' EXIT
redact <"$diagnosis" >"$clean"
# Overwrite the file with the redacted text, so the copy kept in the job
# artefacts is the same text that is posted.
cat "$clean" >"$diagnosis"
{
  echo "**Automated diagnosis of failed job(s), draft, read-only agent.** Pipeline: ${CI_PIPELINE_URL:-unknown}"
  echo
  echo "_This is advice from an agent with read access to the job logs and the repository. It changed nothing. Verify before acting._"
  echo
  head -c "$max_bytes" "$clean"
  if [ "$(wc -c <"$clean")" -gt "$max_bytes" ]; then
    printf '\n\n_(truncated; full text in the job artefacts)_\n'
  fi
} >"$body"

curl --fail --silent --show-error --max-time 30 \
  --request POST \
  --header "PRIVATE-TOKEN: ${DIAGNOSE_API_TOKEN}" \
  --data-urlencode "body@${body}" \
  "${CI_API_V4_URL}/projects/${CI_PROJECT_ID}/merge_requests/${CI_MERGE_REQUEST_IID}/notes" >/dev/null

echo "Posted diagnosis to merge request !${CI_MERGE_REQUEST_IID}"
