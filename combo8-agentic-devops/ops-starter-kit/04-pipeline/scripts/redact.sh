#!/usr/bin/env bash
# Redaction shared by collect-failed-job-logs.sh (logs in) and post-mr-note.sh
# (diagnosis out). Source it; do not run it.
#
#   redact      stdin -> stdout. Removes common secret shapes, credentials in
#               URLs, and the literal values of the job's own secret variables.
#
# Defence in depth, not a promise: GitLab already masks masked variables, and
# the diagnose job keeps the agent away from the environment and .git/. A shape
# this file does not know about still gets through, so add one when you find it.
#
# Environment:
#   DIAGNOSE_REDACT_VARS   extra variable names, space-separated, whose values
#                          are redacted wherever they appear (added to the list
#                          below)

# Variables whose values are secrets in a GitLab job. Values shorter than 8
# characters are skipped, so a short or empty value cannot blank the text.
REDACT_VARS_DEFAULT="DIAGNOSE_API_TOKEN ANTHROPIC_API_KEY CI_JOB_TOKEN CI_JOB_JWT CI_JOB_JWT_V2 \
CI_REGISTRY_PASSWORD CI_DEPENDENCY_PROXY_PASSWORD CI_DEPLOY_PASSWORD CI_REPOSITORY_URL \
GITLAB_OIDC_TOKEN AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN"

redact_shapes() {
  sed -E \
    -e 's/gl(pat|oas|dt|rt|cbt|ptt|ft|imt|agent|soat|ffct|wt)-[A-Za-z0-9_-]{20,}/[REDACTED]/g' \
    -e 's/sk-ant-[A-Za-z0-9_-]{10,}/[REDACTED]/g' \
    -e 's/(AKIA|ASIA)[0-9A-Z]{16}/[REDACTED]/g' \
    -e 's#(://)[^/@[:space:]]+:[^/@[:space:]]+@#\1[REDACTED]@#g' \
    -e 's/(Bearer|bearer) [A-Za-z0-9._~+\/=-]{8,}/\1 [REDACTED]/g' \
    -e 's/((password|PASSWORD|Password|passwd|secret|SECRET|Secret|token|TOKEN|Token|api_key|API_KEY|apikey|ApiKey)["'\'']?[[:space:]]*[:=][[:space:]]*["'\'']?)[^[:space:]"'\'']+/\1[REDACTED]/g' \
    -e '/-----BEGIN [A-Z ]*PRIVATE KEY-----/,/-----END [A-Z ]*PRIVATE KEY-----/c\
[REDACTED PRIVATE KEY]'
}

# Literal values of the named variables, matched as plain strings (no regex),
# line by line. POSIX awk: works with GNU, BusyBox and BSD awk.
redact_values() {
  REDACT_NAMES="$REDACT_VARS_DEFAULT ${DIAGNOSE_REDACT_VARS:-}" awk '
    BEGIN {
      n = split(ENVIRON["REDACT_NAMES"], names, /[[:space:]]+/)
      for (i = 1; i <= n; i++) {
        v = ENVIRON[names[i]]
        if (length(v) >= 8) vals[++m] = v
      }
    }
    {
      line = $0
      for (i = 1; i <= m; i++) {
        out = ""
        while ((p = index(line, vals[i])) > 0) {
          out = out substr(line, 1, p - 1) "[REDACTED]"
          line = substr(line, p + length(vals[i]))
        }
        line = out line
      }
      print line
    }'
}

redact() {
  redact_values | redact_shapes
}
