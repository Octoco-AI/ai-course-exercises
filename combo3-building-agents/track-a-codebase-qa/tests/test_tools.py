"""Tool-level tests."""

from __future__ import annotations


def test_read_file_reads_workspace_file(sandbox):
    tools = sandbox["tools"]
    content = tools.read_file("README.md")
    assert "Sandbox" in content


def test_read_file_missing(sandbox):
    assert sandbox["tools"].read_file("nope.md").startswith("ERROR:")


def test_read_file_escape_attempt(sandbox):
    result = sandbox["tools"].read_file("../../../etc/passwd")
    assert result.startswith("ERROR:")
    assert "outside the sandbox" in result


def test_list_files(sandbox):
    entries = sandbox["tools"].list_files(".")
    assert "README.md" in entries
    assert "src/" in entries


def test_list_files_nested(sandbox):
    assert sandbox["tools"].list_files("src") == ["hello.py"]


def test_search_docs_returns_relevant_hits(sandbox):
    hits = sandbox["tools"].search_docs("how does authentication work", k=3)
    assert len(hits) >= 1
    # First hit should mention sessions (from the auth.md doc).
    assert any("session" in h["text"].lower() for h in hits)
    # Scores should be in [0, 1].
    for h in hits:
        assert 0.0 <= h["score"] <= 1.0


def test_search_docs_empty_query(sandbox):
    hits = sandbox["tools"].search_docs("")
    assert len(hits) == 1
    assert hits[0]["text"].startswith("ERROR:")


def test_draft_patch_creates_patch_file_without_modifying_workspace(sandbox):
    tools = sandbox["tools"]
    original_content = (sandbox["workspace"] / "README.md").read_text()

    result = tools.draft_patch("README.md", "Sandbox", "Reworked Sandbox")
    assert result.startswith("OK: drafted patch at")

    # Workspace is untouched.
    assert (sandbox["workspace"] / "README.md").read_text() == original_content

    # A patch file exists.
    patches = list(sandbox["patches"].glob("*.patch"))
    assert len(patches) == 1
    patch_content = patches[0].read_text()
    assert "-# Sandbox" in patch_content
    assert "+# Reworked Sandbox" in patch_content


def test_draft_patch_rejects_non_unique_old_str(sandbox):
    tools = sandbox["tools"]
    # Create a file with a repeated substring.
    (sandbox["workspace"] / "dup.txt").write_text("foo bar foo baz\n")

    result = tools.draft_patch("dup.txt", "foo", "qux")
    assert result.startswith("ERROR:")
    assert "2 times" in result

    # No patch written on error.
    assert list(sandbox["patches"].glob("*.patch")) == []


def test_draft_patch_rejects_missing_old_str(sandbox):
    tools = sandbox["tools"]
    result = tools.draft_patch("README.md", "not-present-text", "x")
    assert result.startswith("ERROR:")
    assert "not found" in result
