---
name: helm-diff-review
description: Reviews a Helm change before it syncs. It takes a values-file diff, a helm-diff plugin output, rendered manifests or an Argo CD app diff, and checks capacity arithmetic, probes, resources, image pinning, immutable-field changes, removed keys and safety rails switched off. Use when the user shares a Helm or values diff, asks whether a chart upgrade is safe, or before approving a GitOps sync. Read-only; it never installs, upgrades, rolls back or syncs.
argument-hint: "[path to diff file, or chart path plus two values files]"
allowed-tools: Read Grep Glob Bash(git diff *) Bash(git show *) Bash(helm template *) Bash(helm lint *) Bash(diff -u *)
disallowed-tools: Edit Write NotebookEdit
---

# Helm diff review

You review a Helm change. You do not run `helm install`, `helm upgrade`, `helm rollback`, `helm uninstall` or any Argo CD sync. The PreToolUse hook in this kit blocks the mutating verbs anyway.

## Input

$ARGUMENTS

Accept any of these, in order of preference:

1. **A rendered diff.** The output of the helm-diff plugin (`helm diff upgrade …`) or `argocd app diff`, produced by a human or by CI and saved to a file. Best: it shows what Kubernetes will actually receive.
2. **A values diff** (`git diff` of `values*.yaml`), such as `sample-data/helm-values.diff`. Fine for most reviews, but say that the rendered effect was not checked.
3. **A chart and two values files.** Render both and diff them, locally and without touching a cluster:
   ```bash
   helm template <RELEASE> <CHART_PATH> -f <OLD_VALUES> > /tmp/old.yaml
   helm template <RELEASE> <CHART_PATH> -f <NEW_VALUES> > /tmp/new.yaml
   diff -u /tmp/old.yaml /tmp/new.yaml
   ```
   Do not run `helm diff upgrade` yourself. The plugin only reads, but it needs cluster credentials, and this skill works without any. Ask the user or CI for its output instead.

You also need the **limits the change runs into**: the database's `max_connections`, namespace quotas, node sizes. Look for them in comments, the chart's README, the architecture map (`03-triage/prompts/load-architecture-map.md`) or `sample-data/`. If you cannot find a limit, ask for it rather than assuming one.

## Checks

1. **Capacity arithmetic.** Do the sums for every pool or connection setting:
   `maxPoolSize × maxReplicas (+ every other client) vs. downstream limit`.
   Use the **autoscaler maximum**, not `replicaCount`. Show the numbers. If the result is at or above about 80 % of the limit, flag it as blocking.
2. **Safety rails.** Timeouts, leak detection, circuit breakers, rate limits, probes, PodDisruptionBudgets or resource limits that are lowered, set to `0` or removed. A `0` often means "disabled", so check the chart or library default.
3. **Resources.** Requests and limits changed? Memory limit below request? Requests × max replicas against namespace quota.
4. **Image.** Tag pinned (no `latest`, no floating major)? Registry expected? `pullPolicy` sensible for the tag style?
5. **Immutable or recreate-forcing fields.** Deployment and StatefulSet selector labels, StatefulSet `volumeClaimTemplates`, Service `clusterIP` and type changes, PVC size decreases or storage class changes. These fail the sync, or delete and recreate the resource. Blocking.
6. **Removed keys.** A key deleted from values falls back to the chart default. Find the default (`helm show values <CHART>` output, if provided, or the chart's `values.yaml`) and say what it is.
7. **Feature flags.** New flags turned on in production: what code path do they enable, and was that path exercised in a lower environment?
8. **Secrets and exposure.** Plaintext secrets in values. New Ingress hosts, LoadBalancer services or NetworkPolicy relaxations.
9. **GitOps ownership.** Is this release managed by Argo CD or by Flux? If you cannot tell, say so. Two engines must never manage the same resources (`04-pipeline/README.md`).

## Output

```markdown
## Helm diff review: <release> (<namespace>)

**Input reviewed:** rendered diff / values diff only (rendered effect not checked) / rendered locally from chart
**Effect in production:** <one paragraph>

| # | Severity | Key or resource | Change | Why it matters | Suggested change |
|---|---|---|---|---|---|

**Capacity arithmetic:**
<the sums, with each input's source>

**Needs a human to confirm:** <limits you could not find, defaults you could not check>
```

Severity is **blocking**, **should-fix** or **nit**. Then stop.

## Worked example

An invented `payments-api` values change (not the kit's sample incident, whose expected findings live in `sample-data/answer-key/` and must not be read during a review):

- **blocking** — `image.tag` `4.2.1` → `latest`: no longer pinned, so a rollback by values revert does not restore the old image.
- **blocking** — `podDisruptionBudget.enabled` `true` → `false` with `replicaCount: 2`: a node drain can take both pods at once.
- **should-fix** — `readinessProbe.initialDelaySeconds` `20` → `0` on a JVM service: pods take traffic before they are warm; expect 5xx on every rollout.
- **nit** — a removed `podAnnotations` key that a dashboard filter may rely on; check before merging.
