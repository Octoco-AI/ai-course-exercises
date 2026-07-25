"""Guardrail tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.guardrails import (
    FORBIDDEN_ACTIONS,
    GuardrailViolation,
    ensure_within,
    reject_forbidden,
)


def test_ensure_within_allows_child_paths(tmp_path: Path):
    (tmp_path / "a").mkdir()
    resolved = ensure_within("a", tmp_path)
    assert resolved == (tmp_path / "a").resolve()


def test_ensure_within_allows_nested_paths(tmp_path: Path):
    (tmp_path / "a" / "b").mkdir(parents=True)
    resolved = ensure_within("a/b", tmp_path)
    assert resolved == (tmp_path / "a" / "b").resolve()


def test_ensure_within_rejects_parent_traversal(tmp_path: Path):
    with pytest.raises(GuardrailViolation, match="outside the sandbox"):
        ensure_within("../secret", tmp_path)


def test_ensure_within_rejects_absolute_escape(tmp_path: Path):
    with pytest.raises(GuardrailViolation):
        ensure_within("/etc/passwd", tmp_path)


def test_forbidden_actions_blocked():
    for action in FORBIDDEN_ACTIONS:
        with pytest.raises(GuardrailViolation, match="not permitted"):
            reject_forbidden(action)


def test_allowed_actions_pass_through():
    # The four tool names the agent uses — none should be on the forbidden list.
    for allowed in ("search_docs", "read_file", "list_files", "draft_patch"):
        reject_forbidden(allowed)  # should not raise
