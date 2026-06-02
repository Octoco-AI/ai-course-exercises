"""Tool-level tests.

Same shape as Combo 1 M1's tiny-agent tests — the tools are identical. These
confirm the wrapper logic didn't drift when we re-copied the file. Server-
level tests (that run the MCP server and speak protocol to it) are left to
Phase 3 to author, alongside the full running-artefact.
"""

from __future__ import annotations

import pytest

from mcp_filesystem_server.tools import edit_file, list_files, read_file


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    import mcp_filesystem_server.tools as tools_module

    monkeypatch.setattr(tools_module, "_SANDBOX_ROOT", tmp_path.resolve())
    (tmp_path / "hello.txt").write_text("hello world\n")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "deep.txt").write_text("deep content\n")
    monkeypatch.chdir(tmp_path)
    yield tmp_path


def test_read_file(sandbox):
    assert read_file("hello.txt") == "hello world\n"


def test_read_file_missing(sandbox):
    assert read_file("no.txt").startswith("ERROR:")


def test_read_file_escape(sandbox):
    assert read_file("../../etc/passwd").startswith("ERROR:")


def test_list_files(sandbox):
    entries = list_files(".")
    assert "hello.txt" in entries
    assert "nested/" in entries


def test_edit_file(sandbox):
    assert edit_file("hello.txt", "hello", "hi").startswith("OK:")
    assert (sandbox / "hello.txt").read_text() == "hi world\n"


def test_edit_file_non_unique(sandbox):
    (sandbox / "dup.txt").write_text("foo bar foo\n")
    result = edit_file("dup.txt", "foo", "qux")
    assert result.startswith("ERROR:")
    assert "2 times" in result
    # File should not have changed.
    assert (sandbox / "dup.txt").read_text() == "foo bar foo\n"
