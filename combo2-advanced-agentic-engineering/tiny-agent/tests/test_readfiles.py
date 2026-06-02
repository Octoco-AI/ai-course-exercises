"""Evals for <feature>. Run with:
    pytest -m evals tests/evals/
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.evals

from starter.tools import read_file, list_files, edit_file


def test_read_file_returns_content():
    content = read_file("sample_repo/math_utils.py")
    assert "def factorial(" in content
    assert "def gcd(" in content


def test_read_file_nonexistent_returns_error_string():
    content = read_file("no-such-file.py")
    assert content.startswith("ERROR:")
    assert "does not exist" in content  # shape matters


def test_list_files_returns_strings():
    items = list_files("sample_repo")
    assert isinstance(items, list)
    assert all(isinstance(i, str) for i in items)