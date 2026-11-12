# 04-pipeline — agents in the pipeline (m64)

Agents in CI sit at the **recommend** rung. They read logs, diffs and reports, and they write comments and draft MR descriptions. They never hold deploy rights.

| Path | What it is |
|---|---|
| `gitlab-ci.diagnose.yml` | A `.post` job that runs when an MR pipeline fails. It collects the failed jobs' logs, runs Claude Code headless with only Read, Grep and Glob, scoped to the checkout, and posts the redacted diagnosis as an MR comment. Includes an OIDC variant |
| `scripts/collect-failed-job-logs.sh` | Deterministic: fetches failed-job logs via the GitLab API (GET only), strips colour codes, redacts secrets and keeps the tail |
| `scripts/post-mr-note.sh` | Deterministic: redacts the diagnosis again and posts it as an MR note. The agent never touches the API |
| `scripts/redact.sh` | The redaction both scripts share: token and key shapes, credentials in URLs, and the literal values of the job's own secret variables (add more with `DIAGNOSE_REDACT_VARS`) |
| `prompts/diagnose-failed-job.md` | The headless prompt: first real error, classification, `path:line`, next step. Treats log text as data |
| `argo-drift-check.sh` | Read-only Argo CD report: `app list`, `app get` and `app diff`, nothing else. Exit 0 clean, 1 drift, 2 error |
| `prompts/dependency-check.md` | Turns npm and Maven dependency reports into a prioritised plan and a draft MR. Never runs installs |
| `../.claude/skills/mr-review/` | Reviewing an infrastructure or config MR: blast radius, rollback, secrets, destructive changes |
| `../.claude/skills/helm-diff-review/` | Reviewing a Helm values or rendered diff: capacity arithmetic, probes, immutable fields, removed keys |
| `tests/` | `python3 -m pytest 04-pipeline/tests` (stub `argocd`, mock GitLab API, redaction of the outgoing note, the agent's read scope, bash -n, shellcheck) |

## Guardrails

- **Feature branches and non-production runners only.** The diagnose job runs for `merge_request_event` pipelines, on a runner tag that cannot reach production.
- **No deploy rights in the job.** No `environment:`, so environment-scoped deploy credentials never reach it. The API token has the Reporter role: it can read logs and comment, but cannot push, merge or deploy.
- **Log content is untrusted input.** The job runs for MR pipelines, so whoever opens the MR decides what the failed jobs print, including lines written to steer the agent. The prompt tells the agent to quote such lines and carry on, but the prompt only asks: the controls below are what hold if it is steered anyway.
- **Explicit tools.** `--tools "Read,Grep,Glob"` makes those the only built-in tools, a `--disallowedTools` list removes the rest, `--permission-mode dontAsk` refuses anything that would prompt, and `--bare` stops the branch under review loading its own hooks, MCP servers or settings.
- **Reads scoped to the checkout.** The job environment holds the model key and a GitLab token, and the runner's `.git/config` may embed the job token. So `--allowedTools "Read(./**)"` pre-approves reads in the checkout only (which includes `diagnose/`), `blockReadsOutsideWorkingDirectories` refuses everything outside it, and `Read(...)` deny rules name `.git/**`, `/proc`, `/etc`, `/tmp`, home directories and env and credential files explicitly. A deny rule beats an allow rule. Never go back to a bare `--allowedTools "Read,Grep,Glob"`: a bare tool name pre-approves every path on the runner.
- **Redaction both ways.** `scripts/redact.sh` runs over the logs before the agent sees them and over the diagnosis before it is posted, so a secret the agent echoes does not reach the MR. It is defence in depth: a secret shape it does not know still gets through.
- **Deterministic edges.** Scripts fetch the input and post the output. The agent sits in between with no network and no shell.
- **Masked or OIDC credentials.** The model key is a masked variable with a spend limit, or the job uses short-lived OIDC credentials.
- **Kill switch.** Set the `DIAGNOSE_ENABLED` CI/CD variable to `false`.

## Running the drift check

```bash
export ARGOCD_SERVER=<ARGOCD_HOST>            # e.g. argocd.example.internal
# The read-only token from 01-access/ is already set as ARGOCD_API_TOKEN (the name
# argocd-mcp reads); the script passes it to the CLI as ARGOCD_AUTH_TOKEN.
./04-pipeline/argo-drift-check.sh -p <PROJECT> -o drift-report.md
```

One token, two names: the `argocd` CLI reads `ARGOCD_AUTH_TOKEN` and the argocd-mcp server reads `ARGOCD_API_TOKEN`. The script uses `ARGOCD_AUTH_TOKEN` if it is set and falls back to `ARGOCD_API_TOKEN`, so with the kit's `01-access/` setup there is nothing extra to export. In a scheduled CI job, set either one as a masked variable.

As a scheduled CI job, post `drift-report.md` to the team channel or attach it as an artefact. Do **not** follow it with an automatic sync: drift is a question for a human ("who changed this live, and should Git win?"), not a trigger for an agent.

`argocd app diff` compares against the live state Argo CD has cached. The script deliberately does not pass `--refresh` or `--hard-refresh`, because those ask the server to do work. If you need fresher data, trigger a refresh as a separate, human-chosen step.

## The GitOps-engine caveat

Some Kubernetes platforms ship **Flux** as their built-in GitOps engine. Argo CD can run alongside it, but **never let two engines manage the same resources**. They will fight: each reverts the other's changes, and every drift report shows noise. Before you point this kit at a cluster:

- List which engine owns which namespaces or applications, and write it in your team playbook (`06-playbook/`).
- Run the drift check only against applications Argo CD owns. Use `-p` or `-l` to scope it.
- For Flux-managed resources, the equivalent read-only commands are `flux get kustomizations`, `flux get helmreleases` and `flux diff kustomization`. VERIFY: `flux diff` flags on your Flux version. Do not mix the two reports.

## Further reading

- k8sgpt is an open-source Kubernetes diagnosis tool, useful as a reference point for analysis-only cluster triage. Run it in analysis mode only, under the same view-role ServiceAccount as everything else in this kit.
- Claude Code GitLab CI/CD is in beta and maintained by GitLab. Check its docs before you upgrade.
