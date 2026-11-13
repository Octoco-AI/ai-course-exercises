# Claude Code settings for a rung-1 (read-only) ops agent

`settings.example.json` encodes the least-privilege matrix as policy the harness
enforces, independent of what the model decides to do.

## Install

```bash
mkdir -p .claude/hooks
cp <KIT_PATH>/01-access/settings/settings.example.json .claude/settings.json   # or merge into yours
cp <KIT_PATH>/01-access/hooks/block_mutating_ops.py   .claude/hooks/
chmod +x .claude/hooks/block_mutating_ops.py
python3 -m unittest -v <KIT_PATH>/01-access/hooks/test_block_mutating_ops.py   # 14 tests, 240+ cases
```

Commit `.claude/settings.json` so the whole team inherits it. Per-engineer
overrides go in `.claude/settings.local.json`, which is gitignored. Run
`/permissions` in a session to see the rules that are in force.

## What is in it

| Block | What it does |
|---|---|
| `permissions.deny` — `Bash(...)` | Mutating `kubectl`, `helm`, `argocd`, `terraform`/`tofu`, `aws`, `gcloud` and `gsutil` verbs, and the cloud CLIs' secret reads; force-pushes and pushes to `main`/`master`; `glab mr merge`/`approve`. A deny rule is absolute: no prompt, no override by an allow rule. |
| `permissions.deny` — `mcp__...` | Every write tool of the nine MCP servers, by name, so that a server started without its read-only switch still cannot write through Claude Code. |
| `permissions.deny` — `Read(...)` | Kubeconfigs, Argo CD CLI config, AWS credentials, gcloud and Sentry CLI config, `.env` files, keys and `secrets/` directories stay out of the agent's context. The last rule keeps the agent out of the sample incident's answer key (`sample-data/answer-key/`); delete it when you delete `sample-data/`. |
| `permissions.ask` | `git push`, `glab mr create`, `glab ci run`/`retry`, `glab api`, `ansible-playbook`, `terraform plan` — allowed only with a human saying yes each time. |
| `disableBypassPermissionsMode` | Nobody can start this project in `bypassPermissions` mode and skip all of the above. |
| `enabledMcpjsonServers` | Approves the nine servers from the project `.mcp.json` without a prompt. Remove any you do not use. |
| `hooks.PreToolUse` | Runs `block_mutating_ops.py` before every Bash call. |

## Why both deny rules and a hook

They catch different things.

- **Deny rules** match the command text after Claude Code splits `&&`, `;`, `|`
  and subshells, and strip a fixed set of wrappers (`timeout`, `nice`, `nohup`,
  leading variable assignments). They do **not** match `kubectl -n prod delete …`
  (flag before the verb), `sudo kubectl delete …`, `k delete …`,
  `/usr/local/bin/kubectl delete …` or `bash -c '…'`. Claude Code's own docs say a
  Bash rule "isn't a security boundary around the program".
- **The hook** parses the command itself, skips global flags to find the real
  verb, looks through `sudo`, `env`, `xargs`, `watch`, `ssh host '…'`,
  `bash -c`, `eval`, `find -exec`, `setsid`, `script` and aliases (`k` only as
  the command word), and **allowlists** read verbs — anything it does not
  recognise is denied. It fails closed when it cannot parse a command that
  mentions kubectl, helm, argocd, aws, gcloud or gsutil, or cannot see what will run: a command name
  built by a brace expansion or glob (`{kubectl,delete,pod,x}`,
  `/usr/local/bin/kubec*l`), `source <(…)`, a shell fed from a pipe, inline
  Python, Perl or awk, and `tmux`/`screen`/`at`. It also denies
  `kubectl config view` (with `--raw` or `--flatten` it prints credentials; use
  `config current-context` or `config get-contexts`) and Helm's
  `--post-renderer` on every verb, because it runs an executable.
- **For `aws`, `gcloud` and `gsutil`** the hook allowlists by verb shape, because
  the CLIs have hundreds of services: `aws <service> describe-*|list-*|get-*…`,
  `gcloud … list|describe|read|…`. It denies reads that print a secret or token
  (`get-secret-value`, `--with-decryption`, `get-login-password`,
  `gcloud auth print-*`, `secrets versions access`, `get-credentials`) even
  though they are reads.

Neither replaces the credential. A script file the agent runs is not opened by
either layer; a view-role ServiceAccount stops it anyway.

A hook that exits `2` blocks the call before permission rules are evaluated, so
it holds even in `acceptEdits` or `auto` mode, and an allow rule cannot override it.

## Moving to rung 2 (recommend)

When the agent may draft MRs, change only these, in a reviewed MR to this file:

1. Leave `git push` and `glab mr create` in `ask` — a human still says yes to each push.
2. If the agent opens MRs through the GitLab MCP server instead, move
   `mcp__gitlab__add_branch`, `mcp__gitlab__add_commit` and
   `mcp__gitlab__save_merge_request` from `deny` to `ask`. Keep
   `accept_merge_request` and `save_merge_request_review` in `deny`.
3. On the GitLab side, protect the default branch and require a human approval
   (see `../token-checklist.md`).
4. In the same MR, change the `Current rung` line in `CLAUDE.md` / `AGENTS.md` to
   **Recommend**. At Read the rules file tells the agent to describe changes, not
   push them (`00-ladder/ladder.md`).

Nothing in the cluster, cloud, Argo CD or Helm rules changes on rung 2. Changes reach the
cluster only by merge and GitOps.

## Extending the hook

- To allow a new read verb, add it to the right `*_READ_VERBS` set in
  `block_mutating_ops.py` and add an `ALLOW` case to the tests.
- To support another kubectl-compatible client, add its name to `KUBECTL_NAMES`.
- Every bypass you find becomes a `DENY` test case before it becomes a fix.

The hook writes nothing to disk. If you want an audit trail of blocked calls,
add a `PostToolUse` or logging hook rather than growing this one.
