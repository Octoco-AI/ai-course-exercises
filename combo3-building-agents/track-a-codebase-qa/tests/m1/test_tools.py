"""Module 1, Step 3 — tool-level tests.

Run just these with: pytest -m m1 tests/m1/test_tools.py
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.m1


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
    assert "src" in result


def test_list_files_nested(sandbox):
    result = sandbox["tools"].dispatch("list_files", {"path": "src"})
    assert "hello.py" in result


def test_edit_file_replaces_match(sandbox):
    tools = sandbox["tools"]
    result = tools.dispatch(
        "edit_file", {"path": "README.md", "old_str": "Sandbox", "new_str": "Reworked Sandbox"}
    )
    assert "Edited" in result
    assert "Reworked Sandbox" in (sandbox["workspace"] / "README.md").read_text()


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
