"""Guardrails — Track B.

Same sandbox primitive as Track A (`ensure_within`), different forbidden-
actions list. The helpdesk agent:

  - can READ KB articles
  - can DRAFT reply emails (files; a human sends them)
  - can ESCALATE to a human (files; a human reads)

It CANNOT:

  - access any user's actual account data (no `lookup_user`, no `get_billing`).
    The agent always escalates when a user asks about their specific data.
  - send an email, chat message, or external notification.
  - change a user's subscription, password, or 2FA state.
  - delete anything.
"""

from __future__ import annotations

from pathlib import Path


class GuardrailViolation(ValueError):
    """Raised when a tool call is blocked by a guardrail."""


def ensure_within(path: str, root: Path) -> Path:
    """Resolve `path` under `root`; raise if it escapes."""
    try:
        candidate = (root / path).resolve()
    except (OSError, RuntimeError) as exc:
        raise GuardrailViolation(f"could not resolve path {path!r}: {exc}") from exc
    root = root.resolve()
    if not candidate.is_relative_to(root):
        raise GuardrailViolation(f"path {path!r} is outside the sandbox (root={root})")
    return candidate


FORBIDDEN_ACTIONS = frozenset({
    # No direct account access.
    "lookup_user",
    "get_billing_history",
    "get_user_account",
    # No mutations on user accounts.
    "cancel_subscription",
    "reset_password",
    "disable_2fa",
    # No external comms.
    "send_email",
    "send_sms",
    "post_to_slack",
    # No general destructive.
    "delete_file",
    "delete_article",
    "execute_shell",
    "network_request",
})


def reject_forbidden(action_name: str) -> None:
    if action_name in FORBIDDEN_ACTIONS:
        raise GuardrailViolation(
            f"Action {action_name!r} is not permitted. This agent reads the KB, "
            f"drafts replies for a human to send, and escalates when needed. It never "
            f"accesses specific user accounts or takes action on the user's behalf."
        )
