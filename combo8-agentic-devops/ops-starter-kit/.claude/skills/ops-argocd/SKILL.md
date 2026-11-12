---
name: ops-argocd
description: Inspect Argo CD read-only — application health, sync status, drift, history and resource events — through the argocd MCP server in read-only mode or the argocd CLI's read verbs. Use when the user asks whether an app is out of sync, what changed in the last deploy, why an app is degraded, or to run a drift check.
allowed-tools: mcp__argocd__list_applications mcp__argocd__get_application mcp__argocd__get_application_resource_tree mcp__argocd__get_application_managed_resources mcp__argocd__get_application_events mcp__argocd__get_resource_events mcp__argocd__get_resources mcp__argocd__get_application_workload_logs mcp__argocd__list_clusters mcp__argocd__get_appproject Bash(argocd app get *) Bash(argocd app list *) Bash(argocd app diff *) Bash(argocd app history *) Bash(argocd app resources *)
---

# Argo CD, read-only

You can look at Argo CD; you cannot make it do anything. The server runs with
`MCP_READ_ONLY=true`, its token is bound to a read-only role, and the hook blocks
mutating `argocd` verbs. GitOps means the fix for anything you find is a commit to
the config repo, reviewed by a human — never a sync or a `set` from here.

## Before the first query

1. Confirm the **Argo CD instance** and the **application** (and its project).
2. Check whether Argo CD actually manages this resource. Some platforms run Flux as
   their built-in GitOps engine; if the app is not in `list_applications`, say so
   instead of guessing. Two engines must never manage the same resources.

## Query well

- **Status first.** `get_application`: sync status, health status, the revision it
  is synced to, and the target revision. Report those four before anything else.
- **Drift check.** If `OutOfSync`, find *which* resources differ with
  `get_application_managed_resources` or `argocd app diff <APP>`. Summarise the
  diff by resource and field ("replicas 3 → 5 on `deploy/api`, changed in-cluster,
  not in Git"). Do not paste whole manifests.
- **Degraded.** Walk `get_application_resource_tree` to the unhealthy leaf, then
  `get_resource_events` on that resource. Logs (`get_application_workload_logs`)
  last, for one container, tail only.
- **What changed.** `argocd app history <APP>` gives revisions and times; map the
  incident time to the deploy that preceded it, then read that commit in GitLab.

## Never

- Never sync, refresh with `--hard`, set parameters, roll back, delete, terminate
  an operation or run a resource action — not even in a non-production app.
- Never suggest "just sync it" as the fix. Suggest the Git change that would make
  the desired state correct, and who should merge it.
- Never read or print repository credentials or cluster secrets.

## Hand back

A drift or health note: app, instance, sync and health status, synced vs target
revision, the differing resources and fields, the deploy that matches the incident
window, and a recommended Git change (file, field, value) with the reason. If the
drift is an in-cluster manual change, say who should decide whether Git or the
cluster is right.
