---
name: ops-kubernetes
description: Inspect Kubernetes read-only — pods, deployments, events, logs, resource usage and Helm releases — through kubernetes-mcp-server in read-only mode or kubectl and helm read verbs, as a view-role ServiceAccount. Use when the user asks why pods are crashing or pending, what changed in a namespace, or what a workload looked like around an incident.
allowed-tools: mcp__kubernetes__namespaces_list mcp__kubernetes__pods_list mcp__kubernetes__pods_list_in_namespace mcp__kubernetes__pods_get mcp__kubernetes__pods_log mcp__kubernetes__pods_top mcp__kubernetes__resources_list mcp__kubernetes__resources_get mcp__kubernetes__events_list mcp__kubernetes__nodes_top mcp__kubernetes__configuration_contexts_list mcp__kubernetes__helm_list Bash(kubectl get *) Bash(kubectl describe *) Bash(kubectl logs *) Bash(kubectl top *) Bash(kubectl events *) Bash(kubectl auth can-i *) Bash(helm list *) Bash(helm status *) Bash(helm history *) Bash(helm get values *)
---

# Kubernetes, read-only

You act as the `ops-reader` ServiceAccount, which holds the built-in `view` role:
you can get, list and watch, you cannot change anything, read Secrets or exec into
pods. The MCP server runs with `read_only = true` and the hook blocks mutating
`kubectl` and `helm` verbs. If you are blocked, that is the design working.

Put the verb first (`kubectl get pods -n web`, not `kubectl -n web get pods`) so
the pre-approved patterns above match; the hook accepts both.

## Before the first query

1. Confirm the **context** (`configuration_contexts_list` or
   `kubectl config current-context`) and say which cluster you are on. If it is not
   the one the user meant, stop.
2. Confirm the **namespace** and the **workload**. Never sweep `-A` unless the
   question is genuinely cluster-wide.

## Query well

- **Summary before detail.** `kubectl get pods -n <NS> -o wide` and count by
  status. "38 Running, 4 CrashLoopBackOff on node-3" beats forty lines.
- **Events next**, sorted and windowed: `kubectl events -n <NS> --types=Warning`
  or `kubectl get events -n <NS> --sort-by=.lastTimestamp`. Group by reason and
  object.
- **Describe one** failing pod: restarts, last state, exit code, OOMKilled,
  probe failures, scheduling messages.
- **Logs last**, one container, bounded: `kubectl logs <POD> -c <C> --since=15m --tail=200`,
  and `--previous` for a crash. Summarise; quote at most a few lines.
- **Resources**: `kubectl top pods -n <NS> --sort-by=memory` against the pod's
  limits from `describe`.
- **What changed**: `helm history <RELEASE> -n <NS>` and the deployment's
  `kubectl rollout history`, matched to the incident time.

## Never

- Never apply, delete, patch, edit, scale, restart, roll back, drain, cordon,
  exec, port-forward or copy files — and never ask for the hook to be relaxed.
- Never print Secrets or kubeconfigs, or decode base64 values you come across.
- Never stream logs (`-f`) or watch (`-w`) without a timeout; never dump all logs
  of a namespace.

## Hand back

A triage note: cluster, namespace, workload; what is unhealthy and since when;
the evidence (status counts, top event reasons, exit codes, a few log lines); the
most likely cause and how sure you are; and the recommended change as a Git or
Helm values edit for a human to review — "raise the memory limit to 768Mi in
`values-prod.yaml`", not "I restarted it".
