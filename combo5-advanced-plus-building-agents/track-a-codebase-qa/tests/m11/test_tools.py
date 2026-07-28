"""Module 11, Phase 1 — tool-level tests.

Run just these with: pytest -m m11 tests/m11/test_tools.py
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.m11


def test_read_file_reads_workspace_file(sandbox):
    result = sandbox["tools"].dispatch("read_file", {"path": "README.md"})
    assert "Sandbox" in result


def test_read_file_missing_returns_error_string(sandbox):
    result = sandbox["tools"].dispatch("read_file", {"path": "nope.md"})
    assert result.startswith("ERROR:")


def test_read_file_escape_attempt_returns_error_string(sandbox):
    result = sandbox["tools"].dispatch("read_file", {"path": "../../../etc/passwd"})
    assert result.startswith("ERROR:")


def test_list_files_lists_workspace_root(sandbox):
    result = sandbox["tools"].dispatch("list_files", {"path": "."})
    assert "README.md" in result
    assert "src/" in result


def test_list_files_nested(sandbox):
    result = sandbox["tools"].dispatch("list_files", {"path": "src"})
    assert "hello.py" in result


def test_edit_file_replaces_unique_match(sandbox):
    tools = sandbox["tools"]
    result = tools.dispatch(
        "edit_file", {"path": "README.md", "old_str": "Sandbox", "new_str": "Reworked Sandbox"}
    )
    assert "Edited" in result
    assert "Reworked Sandbox" in (sandbox["workspace"] / "README.md").read_text()


def test_edit_file_rejects_non_unique_old_str(sandbox):
    tools = sandbox["tools"]
    (sandbox["workspace"] / "dup.txt").write_text("foo bar foo baz\n")
    result = tools.dispatch("edit_file", {"path": "dup.txt", "old_str": "foo", "new_str": "qux"})
    assert result.startswith("ERROR:")


def test_edit_file_rejects_missing_old_str(sandbox):
    result = sandbox["tools"].dispatch(
        "edit_file", {"path": "README.md", "old_str": "not-present-text", "new_str": "x"}
    )
    assert result.startswith("ERROR:")


def test_dispatch_unknown_tool_returns_error_string(sandbox):
    result = sandbox["tools"].dispatch("delete_everything", {})
    assert result.startswith("ERROR:")


def test_dispatch_bad_arguments_returns_error_string(sandbox):
    result = sandbox["tools"].dispatch("read_file", {"nonexistent_kwarg": "x"})
    assert result.startswith("ERROR:")
