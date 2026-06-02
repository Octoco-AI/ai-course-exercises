"""Guardrails for the four tools.

Two shapes of guardrail:

  1. **Structural** — paths are sandboxed to the workspace root. The agent
     cannot escape, even if the model asks.
  2. **Behavioural** — destructive actions are either blocked entirely
     (no `delete_file`) or stubbed (`draft_patch` writes to a patches/
     directory, never mutates the workspace).

This module has no side effects; all functions are pure-ish checks or
safe file operations that raise on violation.
"""

from __future__ import annotations

from pathlib import Path


class GuardrailViolation(ValueError):
    """Raised when a tool call is blocked by a guardrail."""


def ensure_within(path: str, root: Path) -> Path:
    """Resolve `path` relative to `root` and ensure it doesn't escape.

    Returns the resolved Path on success. Raises GuardrailViolation on escape.
    """
    try:
        candidate = (root / path).resolve()
    except (OSError, RuntimeError) as exc:
        raise GuardrailViolation(f"could not resolve path {path!r}: {exc}") from exc

    # Both must be absolute & already resolved, else is_relative_to can lie.
    root = root.resolve()
    if not candidate.is_relative_to(root):
        raise GuardrailViolation(
            f"path {path!r} is outside the sandbox (root={root})"
        )
    return candidate


# Categories of action the agent is simply not allowed to take. These names
# don't exist as tools, but if a future tool ever tries to do one of these,
# it should consult this list first.
FORBIDDEN_ACTIONS = frozenset({
    "delete_file",
    "delete_directory",
    "execute_shell",
    "network_request",
    "send_email",
    "push_to_remote",
    "commit",
})


def reject_forbidden(action_name: str) -> None:
    """Raise if the action is on the forbidden list."""
    if action_name in FORBIDDEN_ACTIONS:
        raise GuardrailViolation(
            f"Action {action_name!r} is not permitted. This agent is scoped to "
            f"read-only exploration + stubbed PR drafting (via draft_patch)."
        )
