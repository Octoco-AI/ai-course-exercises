"""Module 2 — tool design refinements: ToolError + a tightened description.

Skips at module level until `ToolError` exists in `backend.tools` — that's
the expected state through Module 1.

Run just these with: pytest -m m2 tests/m2/test_tool_design.py
"""

from __future__ import annotations

import backend.tools as tools_module
import pytest

if not hasattr(tools_module, "ToolError"):
    pytest.skip(
        "ToolError not implemented yet — Module 2, Step 4.",
        allow_module_level=True,
    )

pytestmark = pytest.mark.m2


def test_read_file_missing_error_carries_a_suggestion(sandbox):
    result = sandbox["tools"].dispatch("read_file", {"path": "nope.md"})
    assert result.startswith("ERROR:")
    assert "list_files" in result  # the recovery suggestion


def test_read_file_escape_error_carries_a_suggestion(sandbox):
    result = sandbox["tools"].dispatch("read_file", {"path": "../../../etc/passwd"})
    assert result.startswith("ERROR:")
    assert "workspace root" in result or "sandbox" in result


def test_list_files_description_has_a_usage_example(sandbox):
    schemas = sandbox["tools"].schemas()
    list_files_schema = next(s for s in schemas if s["name"] == "list_files")
    assert "example" in list_files_schema["description"].lower()


def test_schemas_are_strict_by_default(sandbox):
    schemas = sandbox["tools"].schemas()
    assert all(s.get("strict") is True for s in schemas)
