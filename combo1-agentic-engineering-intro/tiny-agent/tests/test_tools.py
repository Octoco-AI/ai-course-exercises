"""Smoke tests for the three tools.

Runs against the REFERENCE implementation so attendees can use these as a
contract when they implement their own (in `starter/`).

Run from the tiny-agent/ directory:
    pytest
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# We test the reference implementation. To run the tests against your own
# starter code, replace this import with:
#     from starter.tools import edit_file, list_files, read_file
# (note: the sandbox root is captured at import time, so tests still need to
# be run from a directory that contains the files they look for).
from reference.tools import edit_file, list_files, read_file


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """A temporary directory as the sandbox root for this test.

    Tools compute the sandbox root at import time, so we monkey-patch it on
    the module for the duration of the test.
    """
    import reference.tools as tools_module

    monkeypatch.setattr(tools_module, "_SANDBOX_ROOT", tmp_path.resolve())

    (tmp_path / "hello.txt").write_text("hello world\n")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "deep.txt").write_text("deep content\n")

    monkeypatch.chdir(tmp_path)
    yield tmp_path


# ---- read_file --------------------------------------------------------------


def test_read_file_success(sandbox):
    assert read_file("hello.txt") == "hello world\n"


def test_read_file_nested(sandbox):
    assert read_file("nested/deep.txt") == "deep content\n"


def test_read_file_missing(sandbox):
    result = read_file("does-not-exist.txt")
    assert result.startswith("ERROR:")
    assert "does not exist" in result


def test_read_file_directory_not_file(sandbox):
    result = read_file("nested")
    assert result.startswith("ERROR:")
    assert "not a file" in result


def test_read_file_escape_attempt(sandbox):
    result = read_file("../outside.txt")
    assert result.startswith("ERROR:")
    assert "outside" in result


# ---- list_files -------------------------------------------------------------


def test_list_files_root(sandbox):
    result = list_files(".")
    assert "hello.txt" in result
    assert "nested/" in result


def test_list_files_nested(sandbox):
    result = list_files("nested")
    assert result == ["deep.txt"]


def test_list_files_missing(sandbox):
    result = list_files("no-such-dir")
    assert len(result) == 1
    assert result[0].startswith("ERROR:")


def test_list_files_on_file(sandbox):
    result = list_files("hello.txt")
    assert len(result) == 1
    assert result[0].startswith("ERROR:")


# ---- edit_file --------------------------------------------------------------


def test_edit_file_success(sandbox):
    result = edit_file("hello.txt", "hello", "hi")
    assert result.startswith("OK:")
    assert (sandbox / "hello.txt").read_text() == "hi world\n"


def test_edit_file_missing_old_str(sandbox):
    result = edit_file("hello.txt", "goodbye", "hi")
    assert result.startswith("ERROR:")
    assert "not found" in result


def test_edit_file_non_unique_old_str(sandbox):
    (sandbox / "repeated.txt").write_text("foo bar foo baz\n")
    result = edit_file("repeated.txt", "foo", "qux")
    assert result.startswith("ERROR:")
    assert "2 times" in result
    # File should NOT have been modified on a non-unique match.
    assert (sandbox / "repeated.txt").read_text() == "foo bar foo baz\n"


def test_edit_file_preserves_file_on_error(sandbox):
    original = (sandbox / "hello.txt").read_text()
    edit_file("hello.txt", "nope", "yep")
    assert (sandbox / "hello.txt").read_text() == original
