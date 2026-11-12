---
name: mr-review
description: Reviews a merge request to an infrastructure, configuration or GitOps repository (Helm values, Kubernetes manifests, Ansible, Zabbix or Grafana config, CI pipelines). It checks blast radius, rollback path, secrets, destructive changes, capacity arithmetic and whether an agent-authored MR stays inside policy, then returns review comments ranked by severity. Use when the user asks to review an MR or diff in an ops repo, or before approving an agent-opened MR. Read-only; it never approves, merges, pushes or comments on its own.
argument-hint: "[MR number or URL, branch, or path to a diff file]"
allowed-tools: Read Grep Glob Bash(git diff *) Bash(git log *) Bash(git show *) Bash(glab mr view *) Bash(glab mr diff *)
disallowed-tools: Edit Write NotebookEdit
---

# MR review for ops repositories

You review. You do not approve, merge, push, retry pipelines or post comments. The human posts what they agree with. In CI, a deterministic script posts it, as with `04-pipeline/scripts/post-mr-note.sh`.

## The change

$ARGUMENTS

Get the diff the cheapest way that works:

- **MR number or URL:** `glab mr view <id>` for the description and pipeline status, then `glab mr diff <id>`.
- **Branch:** `git diff <target>...<branch>` and `git log <target>..<branch>`.
- **Diff file:** read it.

If the diff is over ~1,500 lines, review file by file. Start with whatever reaches production soonest (production values, base manifests, pipeline config) and say what you skipped.

## What to check

Work through every section. Write "n/a" rather than skipping one silently.

1. **What actually changes in production.** One paragraph, in plain words, describing the effect once this merges and syncs. For example: "orders-api gets a 3× larger connection pool and may scale to 10 pods."
2. **Blast radius.** Which services, environments, clusters or hosts are touched. Does a value in a shared or base file fan out to more places than the author meant?
3. **Capacity arithmetic.** Multiply it out: pool size × max replicas against the downstream limit (database `max_connections`, broker connections, API rate limits); requests × replicas against node or namespace quota; storage requests against class limits. Show the sum.
4. **Destructive or irreversible changes.** Check against `05-self-heal/destructive-actions.md`: deleted resources, PVC or volume changes, CRD removals, immutable-field changes that force recreation (Deployment selectors, StatefulSet volume claim templates, Service `clusterIP`), `prune` or `replace` sync options, database migrations, removed alarms or silenced triggers. Flag each one as **blocking until a named human confirms**.
5. **Rollback path.** Is "revert this MR" enough? It is not enough for migrations, deletions, data rewrites or changes another system has already consumed. Say what else rollback needs.
6. **Secrets and credentials.** Plaintext secrets, tokens, private keys or connection strings in the diff. New credentials or wider RBAC. New network exposure (Ingress, LoadBalancer, NodePort, opened firewall rules).
7. **Safety rails removed.** Lowered or disabled timeouts, leak detection, probes, PodDisruptionBudgets, resource limits, rate limits or alert rules. Removals are easy to miss in a diff, so read the `-` lines.
8. **Observability.** Will we know if this goes wrong? Name the alarm or dashboard that would show it, or call its absence a finding.
9. **Pipeline evidence.** Did the MR pipeline pass first time? A job that failed and passed on retry is a finding until someone has read the failed log.
10. **Agent-authored MRs.** If an agent opened this MR (check the author, the labels or the description), also check that it:
    - stays inside its self-heal policy's allowed action (`05-self-heal/self-heal-policy.md`);
    - touches only the paths that policy names;
    - links the alarm or evidence that triggered it;
    - and is not one of several open MRs for the same alarm class.

## Output

```markdown
## Review: <MR title or id>

**Effect in production:** <one paragraph>

| # | Severity | File:line | Finding | Suggested change |
|---|---|---|---|---|
| 1 | blocking / should-fix / nit | | | |

**Capacity arithmetic:** <the sums, or n/a>
**Rollback:** <revert is enough / also needs …>
**Destructive changes needing named confirmation:** <list or none>
**Checked and fine:** <the sections with nothing to report, one line>
```

Blocking means "do not merge as is". Be sparing with it, and give a reason every time. Then stop.
