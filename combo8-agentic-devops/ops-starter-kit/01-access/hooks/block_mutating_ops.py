#!/usr/bin/env python3
"""PreToolUse hook: keep an agent's kubectl, helm, argocd, aws, gcloud and gsutil use read-only.

Claude Code runs this before every Bash tool call (see
../settings/settings.example.json for the wiring). It reads the hook payload
as JSON on stdin, looks at ``tool_input.command`` and either:

* exits 0 with no output  -> no decision, the normal permission flow continues
* exits 2 with a reason on stderr -> the call is blocked and the agent is told why

Design choices, in order of importance:

1. **Allowlist, not blocklist.** Only verbs on the read lists below are let
   through. A verb the hook does not know (a new subcommand, a plugin, a value
   flag it mis-parsed) is denied. Adding a read verb is a one-line change you
   make deliberately; a new mutating verb is blocked on day one.
2. **Every command in the line is checked.** ``&&``, ``||``, ``;``, ``|``,
   ``&``, newlines, subshells ``( )``, ``$( )``, backticks, ``bash -c``,
   ``sh -c``, ``eval``, ``watch``, ``xargs``, ``ssh host '...'``, ``sudo``,
   ``env``, ``timeout``, ``find -exec``, ``docker exec``, leading ``VAR=value``
   assignments, shell keywords (``if``/``then``/``do``) and absolute paths
   (``/usr/local/bin/kubectl``) are all looked through. ``setsid``, ``script``
   and ``nohup`` are looked through; ``tmux``/``screen`` and ``at`` are denied
   when they carry a governed binary, and ``tmux send-keys``/``screen -X stuff``
   are denied outright, because typed keystrokes cannot be checked.
3. **Fail closed.** If the command mentions a governed binary (kubectl, helm,
   argocd, aws, gcloud, gsutil) and the hook cannot parse it (unbalanced
   quotes, the command name is a variable, a brace expansion or a glob, an
   inline Python, Perl or awk script, a shell or ``source`` fed from a pipe or
   a process substitution), the call is denied. A command name that is a brace
   expansion or glob which could expand to a governed binary is denied even
   when the line never names one. If the payload itself is not valid JSON and
   mentions those binaries, it is denied.
4. **No credential output, no arbitrary executables.** ``kubectl config view``
   is denied (``--raw`` and ``--flatten`` print credentials; use
   ``config current-context`` or ``config get-contexts``), and so is Helm's
   ``--post-renderer`` on every verb, because it runs an executable of the
   caller's choosing. The cloud CLIs follow the same rule: reads that print a
   secret or a token (``aws secretsmanager get-secret-value``,
   ``aws ecr get-login-password``, ``gcloud auth print-access-token``,
   ``gcloud secrets versions access``, ``gcloud container clusters
   get-credentials``) are denied although they are "reads".

The cloud CLIs have hundreds of services, so their allowlist is by verb
shape rather than by name: an ``aws`` operation is read-only when it starts
``describe-``, ``list-``, ``get-`` and the like; a ``gcloud`` command is
read-only when its verb is ``list``, ``describe``, ``read`` and the like.
Everything else, including verbs the hook has never seen, is denied. One
limit: gcloud's group names and verbs cannot be told apart from the text, so
the first recognised word decides. An unknown write verb followed by a resource
literally named ``list`` would pass. The viewer role is the boundary there.

What this hook is NOT: a security boundary on its own. It checks the command
text the agent writes. A script file the agent runs (``./scripts/fix.sh``)
is not opened. The real boundary is the credential: a view-role
ServiceAccount, a read-only Argo CD account, an IAM role or Google service
account with viewer permissions only, a read-only token (see
../token-checklist.md). This hook is the layer that stops an honest mistake
before it reaches the API and tells the agent what to do instead.

Python 3.8+, standard library only. Tests: test_block_mutating_ops.py.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import sys
from typing import List, Optional, Tuple

# --------------------------------------------------------------------------
# Binaries this hook governs
# --------------------------------------------------------------------------

# kubectl and the names it commonly hides behind. `k` is the near-universal
# alias; `oc` is the OpenShift client and takes the same verbs.
KUBECTL_NAMES = {"kubectl", "k", "kubecolor", "oc", "kubectl.exe"}
HELM_NAMES = {"helm", "helm3", "helm.exe"}
ARGOCD_NAMES = {"argocd", "argocd.exe"}
AWS_NAMES = {"aws", "aws.exe"}
GCLOUD_NAMES = {"gcloud", "gcloud.cmd"}
GSUTIL_NAMES = {"gsutil", "gsutil.cmd"}

GOVERNED_NAMES = (KUBECTL_NAMES | HELM_NAMES | ARGOCD_NAMES
                  | AWS_NAMES | GCLOUD_NAMES | GSUTIL_NAMES)
# `k` is kubectl only as the command word. In argument position
# (`docker exec box k bash`) it is just a letter.
GOVERNED_ARG_NAMES = GOVERNED_NAMES - {"k"}

# Distribution wrappers that run kubectl as a subcommand: `microk8s kubectl get`.
KUBECTL_HOSTS = {"microk8s", "k3s", "k0s"}

# Used only for fail-closed decisions on text we cannot parse.
# Case-insensitive so that `$KUBECTL delete ...` counts as a mention.
MENTION_RE = re.compile(
    r"(?<![\w.])(kubectl|kubecolor|helm3?|argocd|oc|aws|gcloud|gsutil)(?![\w-])"
    r"|(?:^|[\s;&|(`'\"])k(?=\s)",
    re.IGNORECASE,
)

# --------------------------------------------------------------------------
# kubectl
# --------------------------------------------------------------------------

KUBECTL_READ_VERBS = {
    "get", "describe", "logs", "top", "explain", "events", "diff", "wait",
    "api-resources", "api-versions", "cluster-info", "version", "kustomize",
    "completion", "options", "help",
}
# Verbs that are read-only only with certain sub-verbs.
KUBECTL_READ_SUBVERBS = {
    "rollout": {"status", "history"},
    "auth": {"can-i", "whoami"},
    # Not `view`: with --raw or --flatten it prints credentials, and flag
    # spellings are easier to get wrong than a verb. See check_kubectl.
    "config": {"get-contexts", "current-context", "get-clusters", "get-users"},
    "plugin": {"list"},
}
# Named here only so the denial message is specific. Anything not on the read
# lists is denied whether or not it appears here.
KUBECTL_MUTATING = {
    "apply", "create", "delete", "edit", "patch", "replace", "scale", "autoscale",
    "rollout", "drain", "cordon", "uncordon", "taint", "exec", "cp", "attach",
    "run", "expose", "label", "annotate", "set", "debug", "port-forward", "proxy",
    "certificate", "auth", "config",
}
KUBECTL_VALUE_FLAGS = {
    "-n", "--namespace", "--context", "--cluster", "--user", "-s", "--server",
    "--kubeconfig", "--token", "--as", "--as-group", "--as-uid",
    "--request-timeout", "-v", "--v", "--cache-dir", "--certificate-authority",
    "--client-certificate", "--client-key", "--tls-server-name", "--profile",
    "--profile-output", "--log-file", "--username", "--password",
}

# --------------------------------------------------------------------------
# helm
# --------------------------------------------------------------------------

HELM_READ_VERBS = {
    "list", "ls", "status", "get", "history", "hist", "diff", "template",
    "show", "inspect", "search", "version", "env", "lint", "verify",
    "completion", "help",
}
HELM_READ_SUBVERBS = {
    "dependency": {"list", "ls"},
    "dep": {"list", "ls"},
    "repo": {"list", "ls"},
    "plugin": {"list", "ls"},
}
HELM_MUTATING = {
    "install", "upgrade", "rollback", "uninstall", "delete", "del", "un", "test",
    "push", "registry", "repo", "plugin", "dependency", "dep", "create", "package",
    "pull", "fetch",
}
HELM_VALUE_FLAGS = {
    "-n", "--namespace", "--kube-context", "--kubeconfig", "--kube-apiserver",
    "--kube-as-user", "--kube-as-group", "--kube-token", "--kube-ca-file",
    "--kube-tls-server-name", "--registry-config", "--repository-cache",
    "--repository-config", "--burst-limit", "--qps", "--content-cache",
}
# Run an executable of the caller's choosing, on any verb that renders
# (template, lint, show, diff upgrade, ...). Denied wherever they appear.
HELM_EXEC_FLAGS = ("--post-renderer", "--post-renderer-args")

# --------------------------------------------------------------------------
# argocd
# --------------------------------------------------------------------------

ARGOCD_READ_TOP = {"version", "help", "completion"}
ARGOCD_READ_SUBVERBS = {
    "app": {"get", "list", "diff", "history", "manifests", "resources", "logs", "wait"},
    "appset": {"get", "list"},
    "applicationset": {"get", "list"},
    "cluster": {"get", "list"},
    "proj": {"get", "list"},
    "repo": {"get", "list"},
    "repocreds": {"list"},
    "cert": {"list"},
    "gpg": {"get", "list"},
    "account": {"get-user-info", "get", "list", "can-i"},
}
ARGOCD_MUTATING_APP = {
    "sync", "set", "unset", "delete", "rollback", "patch", "create", "edit",
    "terminate-op", "delete-resource", "patch-resource", "actions",
    "add-source", "remove-source", "set-override",
}
ARGOCD_VALUE_FLAGS = {
    "--server", "--auth-token", "--config", "--grpc-web-root-path", "--header",
    "-H", "--http-retry-max", "--logformat", "--loglevel",
    "--port-forward-namespace", "--client-crt", "--client-crt-key",
    "--server-crt", "--kube-context", "--argocd-context", "--redis-haproxy-name",
    "--redis-name", "--repo-server-name", "--server-name", "--controller-name",
    "--redis-compress", "--prompts-enabled",
}

# --------------------------------------------------------------------------
# aws (AWS CLI v2): `aws [global options] <service> <operation> [args]`
# --------------------------------------------------------------------------

AWS_READ_PREFIXES = (
    "describe-", "list-", "get-", "lookup-", "search-", "filter-",
    "batch-get-", "batch-describe-", "simulate-",
)
# Reads that do not follow the naming pattern, per service.
AWS_READ_OPS = {
    "logs": {"start-query", "stop-query", "tail"},
    "s3": {"ls"},
    "configure": {"list", "list-profiles"},
}
AWS_READ_ANY = {"help", "wait"}
# Reads that print a secret or a credential. Denied although they look like reads.
AWS_CREDENTIAL_MARKERS = ("secret-value", "password", "token", "credentials")
AWS_VALUE_FLAGS = {
    "--profile", "--region", "--output", "--query", "--endpoint-url", "--color",
    "--ca-bundle", "--cli-read-timeout", "--cli-connect-timeout",
    "--cli-binary-format",
}

# --------------------------------------------------------------------------
# gcloud: `gcloud [release track] <group> [<group> ...] <verb> [args]`
# --------------------------------------------------------------------------

GCLOUD_RELEASE_TRACKS = {"alpha", "beta", "preview"}
GCLOUD_READ_TOP = {"version", "help", "info", "topic", "cheat-sheet"}
GCLOUD_READ_VERBS = {
    "list", "describe", "read", "tail", "log", "ls", "cat", "du", "get-value",
    "get-iam-policy", "analyze-iam-policy", "search-all-resources",
    "search-all-iam-policies",
}
GCLOUD_READ_PREFIXES = ("list-", "describe-", "get-", "search-")
# Reads that print a secret or a credential, or write one to disk.
GCLOUD_CREDENTIAL_VERBS = {"access", "get-credentials", "configure-docker"}
GCLOUD_CREDENTIAL_PREFIXES = ("print-",)
# Known writes. Used to stop the scan at the verb, so a resource called `list`
# after `delete` cannot make the command look like a read. Anything the hook
# does not recognise is denied anyway. The first command word is a group, never
# the verb, so groups such as `gcloud run` and `gcloud deploy` are not caught.
GCLOUD_MUTATING_VERBS = {
    "create", "delete", "update", "set", "unset", "patch", "apply", "deploy", "ssh",
    "scp", "start", "stop", "restart", "reset", "resize", "suspend", "resume",
    "import", "export", "cp", "mv", "rm", "rsync", "write", "enable", "disable",
    "add", "remove", "submit", "cancel", "rollback", "execute", "call", "invoke",
    "connect", "decrypt", "encrypt", "sign", "activate", "login", "logout",
    "revoke", "attach", "detach", "move", "upload", "init", "install",
    "replace", "promote", "failover", "restore", "clone", "run",
}
GCLOUD_MUTATING_PREFIXES = (
    "add-", "remove-", "set-", "create-", "delete-", "update-", "enable-",
    "disable-", "reset-", "deploy-", "import-", "export-", "generate-",
    "start-", "stop-", "bulk-", "attach-", "detach-", "resume-", "suspend-",
)
GCLOUD_VALUE_FLAGS = {
    "--project", "--account", "--configuration", "--format", "--verbosity",
    "--impersonate-service-account", "--billing-project", "--flags-file",
    "--filter", "--limit", "--page-size", "--sort-by", "--region", "--zone",
    "--location", "--freshness", "--order", "--trace-token",
}

GSUTIL_READ_VERBS = {"ls", "cat", "du", "stat", "version", "help", "hash"}
GSUTIL_VALUE_FLAGS = {"-o", "-h", "-u"}

# --------------------------------------------------------------------------
# Shell structure
# --------------------------------------------------------------------------

SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "ash", "fish"}
INTERPRETERS = {
    "python", "python3", "perl", "ruby", "node", "php", "pwsh", "powershell",
    "deno", "bun", "osascript",
    # awk's system() and `print | "sh"` run commands.
    "awk", "gawk", "mawk", "nawk",
}
# Run commands later or in another terminal. Denied when they carry a governed
# binary; keystroke injection (`tmux send-keys`, `screen -X stuff`) is denied
# outright, because the command can be typed in fragments no parser sees.
DETACHED_RUNNERS = {"tmux", "screen", "byobu", "dtach", "abduco", "zellij", "at", "batch"}
KEYSTROKE_VERBS = {"send-keys", "send", "stuff"}
# Paths a shell or `source` can read a script from without the script being
# in the command text.
STDIN_SCRIPT_RE = re.compile(r"^(?:-|/dev/stdin|/dev/fd/\d+|/proc/(?:self|\d+)/fd/\d+)$")
# The tokeniser writes this for <(...) and >(...); the inner text is checked
# separately, but what it prints is then run by the shell or `source`.
PROCESS_SUBST = "<(...)"
# Names the hook treats specially. A command word that is a glob or brace
# expansion which could produce one of them is checked as that name.
WRAPPER_NAMES = {
    "sudo", "doas", "env", "command", "builtin", "exec", "time", "nohup", "noglob",
    "nocorrect", "unbuffer", "chronic", "nice", "stdbuf", "timeout", "xargs", "watch",
}
GLOB_CHARS = set("*?[")
SHELL_KEYWORDS = {
    "if", "then", "else", "elif", "fi", "do", "done", "while", "until", "!",
    "{", "}", "esac", "function", "coproc",
}
# A loop or case header runs nothing itself; its body is separate commands.
SHELL_HEADERS = {"for", "case", "select"}
# Commands that run another program named in their arguments. The hook looks for
# a governed binary among their arguments and checks from there.
EXEC_LIKE = {
    "find", "parallel", "nsenter", "chroot", "unshare", "flock", "setsid",
    "ionice", "taskset", "strace", "ltrace", "entr", "direnv", "devbox", "mise",
    "asdf", "su", "runuser", "script", "systemd-run", "docker", "podman",
    "nerdctl", "caffeinate", "npx", "pnpx", "bunx",
}
FIND_EXEC = {"-exec", "-execdir", "-ok", "-okdir"}
ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\+?=")

MAX_DEPTH = 6
REMEDY = (
    "This agent is read-only against the cluster, the cloud accounts and the GitOps tooling. "
    "Propose the change as a merge request in the IaC/config repo, "
    "or ask a human to run it."
)


_UNRESOLVED_SCRIPT = (
    "The script passed to a shell or eval is built by a command substitution in a "
    "line that mentions kubectl, helm, argocd, aws, gcloud or gsutil, so the hook cannot see what runs. "
    "Run the command directly."
)


class ParseError(Exception):
    """The command text could not be split into simple commands."""


# --------------------------------------------------------------------------
# Tokeniser
# --------------------------------------------------------------------------

def _read_balanced(s: str, i: int) -> Tuple[str, int]:
    """s[i] is just past an opening '('. Return (inner text, index after ')')."""
    depth = 1
    start = i
    n = len(s)
    while i < n:
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if c == "'":
            j = s.find("'", i + 1)
            if j < 0:
                raise ParseError("unterminated single quote")
            i = j + 1
            continue
        if c == '"':
            i = _skip_double(s, i + 1)
            continue
        if c == "`":
            j = _find_backtick(s, i + 1)
            i = j + 1
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return s[start:i], i + 1
        i += 1
    raise ParseError("unbalanced parentheses")


def _skip_double(s: str, i: int) -> int:
    """i is just past an opening '"'. Return the index after the closing '"'."""
    n = len(s)
    while i < n:
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if c == '"':
            return i + 1
        if c == "$" and i + 1 < n and s[i + 1] == "(":
            _, i = _read_balanced(s, i + 2)
            continue
        if c == "`":
            i = _find_backtick(s, i + 1) + 1
            continue
        i += 1
    raise ParseError("unterminated double quote")


def _find_backtick(s: str, i: int) -> int:
    n = len(s)
    while i < n:
        if s[i] == "\\":
            i += 2
            continue
        if s[i] == "`":
            return i
        i += 1
    raise ParseError("unterminated backtick")


def split_commands(s: str) -> Tuple[List[List[str]], List[str]]:
    """Split shell text into simple commands (lists of words).

    Returns (commands, nested) where nested holds the text of every command
    substitution, backtick, subshell-in-quotes and process substitution found,
    each of which the caller analyses recursively.
    """
    commands: List[List[str]] = []
    nested: List[str] = []
    cmd: List[str] = []
    word: List[str] = []
    in_word = False
    skip_next_word = False
    heredocs: List[Tuple[str, bool]] = []
    pending_heredoc: Optional[bool] = None  # strip-tabs flag while awaiting the delimiter word
    i = 0
    n = len(s)

    def end_word() -> None:
        nonlocal word, in_word, skip_next_word, pending_heredoc
        if in_word:
            text = "".join(word)
            if pending_heredoc is not None:
                heredocs.append((text, pending_heredoc))
                pending_heredoc = None
            elif skip_next_word:
                skip_next_word = False
            else:
                cmd.append(text)
        word = []
        in_word = False

    def end_cmd() -> None:
        nonlocal cmd, skip_next_word
        end_word()
        if pending_heredoc is not None:
            raise ParseError("heredoc operator without a delimiter")
        skip_next_word = False  # a redirect never reaches across a separator
        if cmd:
            commands.append(cmd)
        cmd = []

    while i < n:
        c = s[i]
        if c in " \t\r":
            end_word()
            i += 1
        elif c == "\n":
            end_cmd()
            i += 1
            # Skip heredoc bodies that were opened on the line just ended.
            while heredocs:
                delim, strip_tabs = heredocs.pop(0)
                while i <= n:
                    j = s.find("\n", i)
                    line = s[i:] if j < 0 else s[i:j]
                    i = n if j < 0 else j + 1
                    if (line.lstrip("\t") if strip_tabs else line) == delim:
                        break
                    if j < 0:
                        break
        elif c in ";&|":
            end_cmd()
            i += 1
        elif c in "()":
            end_cmd()
            i += 1
        elif c in "<>":
            if i + 1 < n and s[i + 1] == "(":
                inner, i = _read_balanced(s, i + 2)
                nested.append(inner)
                word.append("<(...)")
                in_word = True
                continue
            if in_word and "".join(word).isdigit():
                word = []
                in_word = False
            end_word()
            j = i
            while j < n and s[j] in "<>&|-":
                j += 1
            op = s[i:j]
            i = j
            if op.startswith("<<<"):
                skip_next_word = True
            elif op.startswith("<<"):
                pending_heredoc = op.endswith("-")
            elif op.endswith("&") and i < n and (s[i].isdigit() or s[i] == "-"):
                i += 1  # 2>&1, >&-
            else:
                skip_next_word = True
        elif c == "#" and not in_word:
            j = s.find("\n", i)
            i = n if j < 0 else j  # leave the newline to end the command
        elif c == "\\":
            if i + 1 < n and s[i + 1] == "\n":
                i += 2  # line continuation
                continue
            if i + 1 < n:
                word.append(s[i + 1])
            in_word = True
            i += 2
        elif c == "'":
            j = s.find("'", i + 1)
            if j < 0:
                raise ParseError("unterminated single quote")
            word.append(s[i + 1:j])
            in_word = True
            i = j + 1
        elif c == '"':
            i += 1
            in_word = True
            while True:
                if i >= n:
                    raise ParseError("unterminated double quote")
                d = s[i]
                if d == "\\" and i + 1 < n:
                    word.append(s[i + 1])
                    i += 2
                elif d == '"':
                    i += 1
                    break
                elif d == "$" and i + 1 < n and s[i + 1] == "(":
                    inner, i = _read_balanced(s, i + 2)
                    nested.append(inner)
                    word.append("$(...)")
                elif d == "`":
                    j = _find_backtick(s, i + 1)
                    nested.append(s[i + 1:j])
                    word.append("$(...)")
                    i = j + 1
                else:
                    word.append(d)
                    i += 1
        elif c == "`":
            j = _find_backtick(s, i + 1)
            nested.append(s[i + 1:j])
            word.append("$(...)")
            in_word = True
            i = j + 1
        elif c == "$" and i + 1 < n and s[i + 1] == "(":
            if i + 2 < n and s[i + 2] == "(":
                _, i = _read_balanced(s, i + 2)  # $(( arithmetic )) runs nothing
                word.append("0")
            else:
                inner, i = _read_balanced(s, i + 2)
                nested.append(inner)
                word.append("$(...)")
            in_word = True
        elif c == "$" and i + 1 < n and s[i + 1] == "'":
            j = i + 2
            while j < n and s[j] != "'":
                j += 2 if s[j] == "\\" else 1
            if j >= n:
                raise ParseError("unterminated $'...'")
            word.append(s[i + 2:j].encode().decode("unicode_escape", "ignore"))
            in_word = True
            i = j + 1
        elif c == "$" and i + 1 < n and s[i + 1] == "{":
            j = s.find("}", i + 2)
            if j < 0:
                raise ParseError("unterminated ${")
            word.append(s[i:j + 1])
            in_word = True
            i = j + 1
        else:
            word.append(c)
            in_word = True
            i += 1

    end_cmd()
    return commands, nested


# --------------------------------------------------------------------------
# Analysis
# --------------------------------------------------------------------------

def mentions_governed_binary(text: str) -> bool:
    return bool(MENTION_RE.search(text))


def _basename(word: str) -> str:
    return os.path.basename(word) if "/" in word else word


def _skip_options(words: List[str], value_flags: set, stop_at_dashdash: bool = True) -> List[str]:
    """Drop leading options (and the values of known value-taking options)."""
    i = 0
    while i < len(words):
        w = words[i]
        if w == "--" and stop_at_dashdash:
            return words[i + 1:]
        if not w.startswith("-") or w == "-":
            break
        if w in value_flags:
            i += 2
        else:
            i += 1
    return words[i:]


def _positionals(args: List[str], value_flags: set) -> List[str]:
    """Non-option words, skipping the values of known value-taking options."""
    out: List[str] = []
    i = 0
    while i < len(args):
        w = args[i]
        if w == "--":
            out.extend(args[i + 1:])
            break
        if w.startswith("-") and w != "-":
            i += 2 if w in value_flags else 1
            continue
        out.append(w)
        i += 1
    return out


def _strip_wrappers(words: List[str], depth: int) -> Tuple[List[str], Optional[str]]:
    """Peel sudo/env/timeout/... off the front. Returns (words, deny_reason)."""
    for _ in range(20):
        while words and (ASSIGNMENT_RE.match(words[0]) or words[0] in SHELL_KEYWORDS):
            words = words[1:]
        if words and words[0] in SHELL_HEADERS:
            return [], None
        if not words:
            return words, None
        head = _basename(words[0])
        rest = words[1:]
        if head in {"sudo", "doas"}:
            words = _skip_options(rest, {"-u", "-g", "-h", "-p", "-C", "-T", "-r", "-t", "-U", "-D", "--user", "--group"})
        elif head == "env":
            # `env -S "kubectl delete ..."` splits its argument into a command.
            for idx, w in enumerate(rest):
                if w in {"-S", "--split-string"} and idx + 1 < len(rest):
                    return [], analyse(rest[idx + 1], depth + 1)
                if w.startswith("--split-string="):
                    return [], analyse(w.split("=", 1)[1], depth + 1)
            words = _skip_options(rest, {"-u", "--unset", "-C", "--chdir"})
        elif head in {"command", "builtin"}:
            if rest and rest[0] in {"-v", "-V"}:
                return [], None  # lookup only, runs nothing
            words = _skip_options(rest, set())
        elif head == "exec":
            words = _skip_options(rest, {"-a"})
        elif head in {"time", "nohup", "noglob", "nocorrect", "unbuffer", "chronic"}:
            words = _skip_options(rest, set())
        elif head == "nice":
            words = _skip_options(rest, {"-n", "--adjustment"})
        elif head == "stdbuf":
            words = _skip_options(rest, {"-i", "-o", "-e"})
        elif head == "timeout":
            words = _skip_options(rest, {"-s", "--signal", "-k", "--kill-after"})
            words = words[1:]  # the duration
        elif head == "xargs":
            words = _skip_options(rest, {"-a", "-d", "-E", "-I", "-L", "-n", "-P", "-s",
                                         "--arg-file", "--delimiter", "--max-args",
                                         "--max-procs", "--max-lines", "--replace"})
        elif head == "watch":
            # watch joins its arguments and runs them through `sh -c`.
            cmd = _skip_options(rest, {"-n", "--interval", "-q", "--equexit"})
            return [], analyse(" ".join(cmd), depth + 1)
        else:
            return words, None
    return words, None


def _fmt(*parts: str) -> str:
    return "`" + " ".join(p for p in parts if p) + "`"


def _find_brace(word: str) -> Optional[Tuple[int, int, List[str]]]:
    """First top-level `{a,b}` or `{x..y}` in word: (start, end, alternatives).

    A sequence `{x..y}` is over-approximated as the glob `*`.
    """
    depth, start = 0, -1
    for i, c in enumerate(word):
        if c == "{":
            if depth == 0:
                start = i
            depth += 1
        elif c == "}" and depth:
            depth -= 1
            if depth == 0:
                inner = word[start + 1:i]
                parts, level, cur = [], 0, []
                for d in inner:
                    if d == "," and level == 0:
                        parts.append("".join(cur))
                        cur = []
                        continue
                    level += (d == "{") - (d == "}")
                    cur.append(d)
                parts.append("".join(cur))
                if len(parts) > 1:
                    return start, i, parts
                if ".." in inner:
                    return start, i, ["*"]
    return None


def _brace_expand(word: str, limit: int = 256) -> Optional[List[str]]:
    """Every word a brace expansion can produce, or None if there are too many."""
    out: List[str] = []
    todo = [word]
    while todo:
        w = todo.pop()
        found = _find_brace(w)
        if found is None:
            out.append(w)
        else:
            start, end, parts = found
            todo.extend(w[:start] + p + w[end + 1:] for p in parts)
        if len(out) + len(todo) > limit:
            return None
    return out


def _is_expansion(word: str) -> bool:
    """True if the shell would brace-expand or glob this word. `[` and `[[` are test."""
    if word in {"[", "[["}:
        return False
    return bool(GLOB_CHARS & set(word)) or _find_brace(word) is not None


def _could_match(word: str, names: set) -> List[str]:
    """The names in `names` that a brace/glob word's basename could expand to."""
    expansions = _brace_expand(word)
    if expansions is None:
        return sorted(names)  # too many to enumerate: assume the worst
    hits = set()
    for e in expansions:
        base = os.path.basename(e) if "/" in e else e
        if not base:
            continue
        hits.update(n for n in names if fnmatch.fnmatchcase(n, base))
    return sorted(hits)


_SPECIAL_NAMES = (
    GOVERNED_NAMES | KUBECTL_HOSTS | {"minikube", "eval", "ssh", "source", "."}
    | SHELLS | INTERPRETERS | EXEC_LIKE | WRAPPER_NAMES | DETACHED_RUNNERS
)


def _unseen_script(args: List[str]) -> bool:
    """A process substitution or stdin path among the arguments."""
    return any(a == PROCESS_SUBST or STDIN_SCRIPT_RE.match(a) for a in args)


def check_kubectl(name: str, args: List[str]) -> Optional[str]:
    pos = _positionals(args, KUBECTL_VALUE_FLAGS)
    if not pos or args[:1] in (["--help"], ["-h"]):
        return None
    verb = pos[0]
    if verb in KUBECTL_READ_VERBS:
        return None
    if verb in KUBECTL_READ_SUBVERBS:
        sub = pos[1] if len(pos) > 1 else ""
        if sub in KUBECTL_READ_SUBVERBS[verb]:
            return None
        if verb == "config" and sub == "view":
            return (f"`{name} config view` is not allowed: with --raw or --flatten it prints "
                    "cluster credentials into the agent's context. Use "
                    f"`{name} config current-context` or `{name} config get-contexts`.")
        return f"{_fmt(name, verb, sub)} is not a read-only command. {REMEDY}"
    if verb in KUBECTL_MUTATING:
        return f"`{name} {verb}` changes cluster state. {REMEDY}"
    return f"`{name} {verb}` is not on this hook's read-only allowlist. {REMEDY}"


def check_helm(name: str, args: List[str]) -> Optional[str]:
    for a in args:  # anywhere, even after `--`: fail closed
        if any(a == f or a.startswith(f + "=") for f in HELM_EXEC_FLAGS):
            return (f"`{name} ... {a.split('=', 1)[0]}` runs an executable of the caller's "
                    "choosing, so it is denied on every helm verb. Render without it, "
                    f"or ask a human to run it. {REMEDY}")
    pos = _positionals(args, HELM_VALUE_FLAGS)
    if not pos:
        return None
    verb = pos[0]
    if verb in HELM_READ_VERBS:
        return None
    if verb in HELM_READ_SUBVERBS:
        sub = pos[1] if len(pos) > 1 else ""
        if sub in HELM_READ_SUBVERBS[verb]:
            return None
        return f"{_fmt(name, verb, sub)} is not a read-only command. {REMEDY}"
    if verb in HELM_MUTATING:
        return (f"`{name} {verb}` changes releases or local Helm state. "
                f"Use `helm diff upgrade` or `helm template` to show the change. {REMEDY}")
    return f"`{name} {verb}` is not on this hook's read-only allowlist. {REMEDY}"


def check_argocd(name: str, args: List[str]) -> Optional[str]:
    pos = _positionals(args, ARGOCD_VALUE_FLAGS)
    if not pos:
        return None
    group = pos[0]
    if group in ARGOCD_READ_TOP:
        return None
    sub = pos[1] if len(pos) > 1 else ""
    if group in ARGOCD_READ_SUBVERBS:
        if sub in ARGOCD_READ_SUBVERBS[group]:
            return None
        if group == "app" and sub == "actions" and len(pos) > 2 and pos[2] == "list":
            return None
        if group == "app" and sub in ARGOCD_MUTATING_APP:
            return f"`{name} app {sub}` changes what Argo CD deploys. {REMEDY}"
        return f"{_fmt(name, group, sub)} is not a read-only command. {REMEDY}"
    if group in {"login", "relogin", "logout", "context"} and not (group == "context" and not sub):
        return f"`{name} {group}` changes the session's Argo CD identity or target. A human logs in. {REMEDY}"
    if group == "context":
        return None  # bare `argocd context` lists contexts
    return f"`{name} {group}` is not on this hook's read-only allowlist. {REMEDY}"


def check_aws(name: str, args: List[str]) -> Optional[str]:
    pos = _positionals(args, AWS_VALUE_FLAGS)
    if len(pos) < 2 or pos[0] == "help" or pos[1] in {"help", "wait"}:
        return None  # `aws --version`, `aws logs`, `aws logs help`, `aws ec2 wait ...`
    service, op = pos[0], pos[1]
    if any(m in op for m in AWS_CREDENTIAL_MARKERS) or (
        service == "ssm" and any(a.startswith("--with-decryption") for a in args)
    ):
        return (f"`{name} {service} {op}` prints a secret or a credential into the agent's "
                "context. Ask a human to read it, or use the metadata call "
                "(`describe-secret`, `get-parameter` without decryption).")
    if op.startswith(AWS_READ_PREFIXES) or op in AWS_READ_OPS.get(service, set()):
        return None
    return f"`{name} {service} {op}` is not a read-only AWS operation. {REMEDY}"


def check_gcloud(name: str, args: List[str]) -> Optional[str]:
    pos = _positionals(args, GCLOUD_VALUE_FLAGS)
    if pos and pos[0] in GCLOUD_RELEASE_TRACKS:
        pos = pos[1:]
    if not pos or pos[0] in GCLOUD_READ_TOP:
        return None
    for word in pos[1:]:
        if word in GCLOUD_CREDENTIAL_VERBS or word.startswith(GCLOUD_CREDENTIAL_PREFIXES):
            return (f"`{name} {' '.join(pos[:pos.index(word) + 1])}` prints or stores a secret "
                    "or a credential. Ask a human to run it.")
        if word in GCLOUD_READ_VERBS or word.startswith(GCLOUD_READ_PREFIXES):
            return None
        if word in GCLOUD_MUTATING_VERBS or word.startswith(GCLOUD_MUTATING_PREFIXES):
            return f"`{name} {' '.join(pos[:pos.index(word) + 1])}` changes cloud state. {REMEDY}"
    return f"`{name} {' '.join(pos[:3])}` is not on this hook's read-only allowlist. {REMEDY}"


def check_gsutil(name: str, args: List[str]) -> Optional[str]:
    pos = _positionals(args, GSUTIL_VALUE_FLAGS)
    if not pos or pos[0] in GSUTIL_READ_VERBS:
        return None
    return f"`{name} {pos[0]}` is not a read-only gsutil command. {REMEDY}"


def check_simple(words: List[str], raw: str, depth: int) -> Optional[str]:
    words, reason = _strip_wrappers(words, depth)
    if reason or not words:
        return reason
    head = _basename(words[0])
    args = words[1:]

    if "$" in words[0] or "(...)" in words[0]:
        if mentions_governed_binary(raw):
            return ("The command name is a variable or substitution in a line that "
                    "mentions kubectl, helm, argocd, aws, gcloud or gsutil, so the hook cannot tell what runs. "
                    "Write the command out literally.")
        return None

    if _is_expansion(words[0]):
        # `{kubectl,delete,pod,x}` and `/usr/local/bin/kubec*l delete pod x`: the
        # shell builds the command name, so the literal text names nothing.
        governed = _could_match(words[0], GOVERNED_NAMES | KUBECTL_HOSTS | {"minikube"})
        if governed or mentions_governed_binary(raw):
            return ("The command name is a brace expansion or glob"
                    + (f" that could expand to `{governed[0]}`" if governed else
                       " in a line that mentions kubectl, helm, argocd, aws, gcloud or gsutil")
                    + ", so the hook cannot tell what runs. Write the command name out literally.")
        for name in _could_match(words[0], _SPECIAL_NAMES):
            reason = check_simple([name] + args, raw, depth + 1)
            if reason:
                return reason
        return None

    if head in KUBECTL_NAMES:
        return check_kubectl(head, args)
    if head in KUBECTL_HOSTS and args[:1] == ["kubectl"]:
        return check_kubectl(f"{head} kubectl", args[1:])
    if head == "minikube" and args[:1] == ["kubectl"]:
        inner = args[1:]
        if "--" in inner:
            inner = inner[inner.index("--") + 1:]
        return check_kubectl("minikube kubectl", inner)
    if head in HELM_NAMES:
        return check_helm(head, args)
    if head in ARGOCD_NAMES:
        return check_argocd(head, args)
    if head in AWS_NAMES:
        return check_aws(head, args)
    if head in GCLOUD_NAMES:
        return check_gcloud(head, args)
    if head in GSUTIL_NAMES:
        return check_gsutil(head, args)

    if head in SHELLS:
        for idx, w in enumerate(args):
            if w.startswith("-") and not w.startswith("--") and "c" in w[1:]:
                script = next((a for a in args[idx + 1:] if not a.startswith("-")), "")
                if "$(...)" in script and mentions_governed_binary(raw):
                    return _UNRESOLVED_SCRIPT
                return analyse(script, depth + 1)
        operands = [a for a in args if not a.startswith("-") or a == "-"]
        reads_stdin = any(a.startswith("-") and not a.startswith("--") and "s" in a[1:] for a in args)
        # Shell reading its script from stdin (`... | bash`, `bash <<EOF`,
        # `bash -s arg`) or from a process substitution (`bash <(...)`).
        if (not operands or reads_stdin or _unseen_script(operands[:1])) and mentions_governed_binary(raw):
            return ("A shell reading commands from a pipe, heredoc or process substitution "
                    "in a line that mentions kubectl, helm, argocd, aws, gcloud or gsutil cannot be checked. "
                    "Run the command directly.")
        return None  # a script file: not opened (see module docstring)

    if head in {"source", "."}:
        # `source <(echo kubectl delete pod x)`, `... | source /dev/stdin`.
        if _unseen_script(args[:1]) and mentions_governed_binary(raw):
            return ("`source` of a process substitution or stdin in a line that mentions "
                    "kubectl, helm, argocd, aws, gcloud or gsutil cannot be checked. Run the command directly.")
        return None  # a script file: not opened (see module docstring)

    if head in DETACHED_RUNNERS:
        if any(a in KEYSTROKE_VERBS for a in args):
            return (f"`{head}` keystroke injection types a command into another terminal, "
                    "where the hook cannot check it. Run the command directly.")
        if mentions_governed_binary(raw):
            return (f"`{head}` runs its command later or in another terminal, where the hook "
                    "cannot check it, in a line that mentions kubectl, helm, argocd, aws, gcloud or gsutil. "
                    "Run the command directly.")
        return None

    if head == "eval":
        if any("$(...)" in a for a in args) and mentions_governed_binary(raw):
            return _UNRESOLVED_SCRIPT
        return analyse(" ".join(args), depth + 1)

    if head in EXEC_LIKE:
        for idx, w in enumerate(args):
            if _basename(w) in GOVERNED_ARG_NAMES or w in KUBECTL_HOSTS:
                inner = args[idx:]
                for stop in (";", "+"):
                    if head == "find" and stop in inner:
                        inner = inner[:inner.index(stop)]
                return check_simple(inner, raw, depth + 1)
            if " " in w and mentions_governed_binary(w):
                return analyse(w, depth + 1)
            # `setsid /usr/local/bin/kubec*l delete pod x`. For find, only the
            # word after -exec is a command; `-name 'h*'` is a pattern.
            in_command_slot = head != "find" or (idx and args[idx - 1] in FIND_EXEC)
            if (in_command_slot and _is_expansion(w)
                    and re.search(r"[A-Za-z0-9]", _basename(w))
                    and _could_match(w, GOVERNED_ARG_NAMES | KUBECTL_HOSTS)):
                return (f"`{head}` runs `{w}`, a glob or brace expansion that could expand to "
                        "kubectl, helm, argocd, aws, gcloud or gsutil. Write the command name out literally.")
        return None

    if head == "ssh":
        rest = _skip_options(args, {"-b", "-c", "-D", "-E", "-e", "-F", "-I", "-i", "-J",
                                    "-L", "-l", "-m", "-O", "-o", "-p", "-Q", "-R", "-S",
                                    "-W", "-w", "-B"})
        remote = rest[1:]
        if remote:
            return analyse(" ".join(remote), depth + 1)
        if mentions_governed_binary(raw):
            return ("ssh without a remote command, in a line that mentions kubectl, helm "
                    "or argocd, cannot be checked. Run the command directly.")
        return None

    if head in INTERPRETERS or re.match(r"^python3(\.\d+)?$", head):
        if mentions_governed_binary(" ".join(args)) or (
            not [a for a in args if not a.startswith("-")] and mentions_governed_binary(raw)
        ):
            return (f"An inline {head} script that mentions kubectl, helm, argocd, aws, gcloud or gsutil cannot "
                    "be checked. Run the command directly so the hook can read it.")
        return None

    return None


def analyse(command: str, depth: int = 0) -> Optional[str]:
    """Return a denial reason, or None if every command in the text is allowed."""
    if depth > MAX_DEPTH:
        return "Command nesting is too deep to check. Simplify the command." if mentions_governed_binary(command) else None
    try:
        commands, nested = split_commands(command)
    except ParseError as exc:
        if mentions_governed_binary(command):
            return f"Could not parse the command ({exc}) and it mentions kubectl, helm, argocd, aws, gcloud or gsutil. Fail closed."
        return None
    for inner in nested:
        reason = analyse(inner, depth + 1)
        if reason:
            return reason
    for words in commands:
        reason = check_simple(words, command, depth)
        if reason:
            return reason
    return None


def decide(payload_text: str) -> Optional[str]:
    try:
        payload = json.loads(payload_text)
    except ValueError:
        if mentions_governed_binary(payload_text):
            return "Hook payload was not valid JSON and mentions kubectl, helm, argocd, aws, gcloud or gsutil. Fail closed."
        return None
    if not isinstance(payload, dict) or payload.get("tool_name") != "Bash":
        return None
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str):
        if mentions_governed_binary(json.dumps(tool_input)):
            return "Bash tool_input has no readable command string. Fail closed."
        return None
    return analyse(command)


def main() -> int:
    reason = decide(sys.stdin.read())
    if reason:
        print(f"Blocked by block_mutating_ops: {reason}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
