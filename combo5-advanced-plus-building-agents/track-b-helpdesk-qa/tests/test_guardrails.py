"""Guardrail tests — Track B."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.guardrails import (
    FORBIDDEN_ACTIONS,
    GuardrailViolation,
    ensure_within,
    reject_forbidden,
)


def test_ensure_within_allows_child(tmp_path: Path):
    (tmp_path / "a").mkdir()
    assert ensure_within("a", tmp_path) == (tmp_path / "a").resolve()


def test_ensure_within_rejects_traversal(tmp_path: Path):
    with pytest.raises(GuardrailViolation, match="outside the sandbox"):
        ensure_within("../escape", tmp_path)


def test_forbidden_actions_block_user_data_access():
    for action in ("lookup_user", "get_billing_history", "get_user_account"):
        with pytest.raises(GuardrailViolation):
            reject_forbidden(action)


def test_forbidden_actions_block_mutations():
    for action in ("cancel_subscription", "reset_password", "disable_2fa"):
        with pytest.raises(GuardrailViolation):
            reject_forbidden(action)


def test_forbidden_actions_block_external_comms():
    for action in ("send_email", "send_sms", "post_to_slack"):
        with pytest.raises(GuardrailViolation):
            reject_forbidden(action)


def test_allowed_tools_pass_through():
    for tool in ("search_kb", "read_article", "create_draft_reply", "escalate_to_human"):
        reject_forbidden(tool)  # should not raise


def test_forbidden_list_is_frozen():
    # Catches accidental mutation; FORBIDDEN_ACTIONS is meant to be immutable.
    with pytest.raises(AttributeError):
        FORBIDDEN_ACTIONS.add("new_action")  # type: ignore[attr-defined]
