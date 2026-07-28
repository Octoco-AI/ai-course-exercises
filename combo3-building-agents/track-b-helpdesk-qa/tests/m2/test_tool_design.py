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


def test_read_ticket_missing_error_carries_a_suggestion(sandbox):
    result = sandbox["tools"].dispatch("read_ticket", {"ticket_id": "TKT-99999"})
    assert result.startswith("ERROR:")
    assert "list_tickets" in result


def test_read_ticket_escape_error_carries_a_suggestion(sandbox):
    result = sandbox["tools"].dispatch("read_ticket", {"ticket_id": "../../../etc/passwd"})
    assert result.startswith("ERROR:")


def test_list_tickets_description_has_a_usage_example(sandbox):
    schemas = sandbox["tools"].schemas()
    list_tickets_schema = next(s for s in schemas if s["name"] == "list_tickets")
    assert "example" in list_tickets_schema["description"].lower()


def test_schemas_are_strict_by_default(sandbox):
    schemas = sandbox["tools"].schemas()
    assert all(s.get("strict") is True for s in schemas)
