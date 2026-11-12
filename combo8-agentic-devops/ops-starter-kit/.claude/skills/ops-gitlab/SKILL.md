---
name: ops-gitlab
description: Read GitLab — merge requests, diffs, pipelines, job logs, repository files and commits — through the GitLab MCP server or glab read commands, without merging, approving, pushing or running anything. Use when the user asks why a pipeline failed, what an MR changes, which commit went out in a deploy, or what a config file says.
allowed-tools: mcp__gitlab__get_project mcp__gitlab__list_projects mcp__gitlab__search mcp__gitlab__get_merge_request mcp__gitlab__list_merge_requests mcp__gitlab__get_pipeline mcp__gitlab__list_pipelines mcp__gitlab__get_job mcp__gitlab__get_repository_file mcp__gitlab__list_repository_tree mcp__gitlab__list_commits mcp__gitlab__get_commit mcp__gitlab__list_branches mcp__gitlab__list_tags Bash(glab mr view *) Bash(glab mr diff *) Bash(glab mr list *) Bash(glab ci list *)
---

# GitLab, read-only

You can read projects, MRs, pipelines and job logs. You cannot merge, approve,
push, comment, create branches or run pipelines — those tools are denied in
settings, and `git push` and `glab mr create` need a human to say yes.

On rung 2 (recommend) you may *propose* a change: commit on a branch named
`agent/<topic>`, push it when the human approves the prompt, and open a **draft**
MR. You still never merge or approve, including your own MR.

<!-- VERIFY: GitLab's tools reference marks some read tools (MR diffs, MR notes,
     pipeline jobs) as callable but no longer listed in tools/list, so Claude Code
     may not offer them. The CLI fallbacks below cover the gap. Check `/mcp`. -->

## Before the first query

1. Confirm the **project** (path, not just a name) and the **ref** — branch, tag
   or MR number.
2. For a pipeline question, get the pipeline id first (`list_pipelines` filtered
   by ref and status, newest first). Do not scan all pipelines.

## Query well

- **Failed pipeline.** `get_pipeline` (or `glab ci list`) → its jobs → pick the
  *first* failed job in stage order (later failures are usually knock-on). Then
  `get_job` for its log and read the **last 100–200 lines** first — the error
  is almost always near the end. Quote the failing command and the error line,
  not the whole log.
- **Known flake or real failure?** Compare with the same job on the previous
  green pipeline of that ref: same error before? Different runner? Changed
  dependency? Say which, with the evidence.
- **MR review.** `get_merge_request` for intent, then the diff (`glab mr diff <IID>`)
  grouped by file. For ops repos, call out anything touching production values,
  RBAC, network policies, secrets references, resource limits or replica counts.
- **What went out.** For a deploy at a given time, `list_commits` on the deploy
  branch around that time, then `get_commit` on the candidates.

## Never

- Never merge, approve, unapprove, close or rebase an MR.
- Never retry, cancel, run or delete a pipeline or job. Recommend a retry; a human
  presses it.
- Never push to the default branch or any protected branch; never force-push.
- Never print CI variables, job tokens or anything that looks like a secret in a
  job log — say "a credential appears in the log at line N" and recommend rotation.

## Hand back

For a failure: pipeline, job, stage, the failing command, the error, whether it
looks like a flake, a code change or an environment problem, and the smallest fix
as a proposed diff. For a review: a short list of findings by file and severity,
and what you could not check.
