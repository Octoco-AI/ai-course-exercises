"""Three file-system tools the agent can call — the same three from the
Combo 1 / Combo 2 M1 tiny-agent.

  - read_file(path)                    — read a file and return its contents
  - list_files(path=".")               — list entries in a directory
  - edit_file(path, old_str, new_str)  — replace old_str with new_str, exactly once

You should not need to edit this file. The model reads the docstrings and type
hints below to decide how to call each tool — they ARE the tool schema, so keep
them clear if you do change them.

Sandbox: every path is resolved against the WORKSPACE directory (set in .env,
default ../expense-categoriser) and rejected if it escapes. The agent can read
and edit files in your target repo, but cannot wander the rest of your machine.
Errors are returned as strings, not raised — the model reads the message and
self-corrects; a stack trace would just confuse it.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env so WORKSPACE is available whether tools.py is imported first or not.
load_dotenv()

# The repo the agent operates on. Resolved once at import time.
_SANDBOX_ROOT = Path(os.environ.get("WORKSPACE", "../expense-categoriser")).resolve()


def workspace_root() -> Path:
    """The directory the agent's tools are sandboxed to. Used by the run scripts
    to print where edits will land."""
    return _SANDBOX_ROOT


def _resolve(path: str) -> Path | str:
    """Resolve ``path`` against the sandbox root, or return an error string."""
    try:
        candidate = (_SANDBOX_ROOT / path).resolve()
    except (OSError, RuntimeError) as exc:
        return f"ERROR: could not resolve path {path!r}: {exc}"
    if not candidate.is_relative_to(_SANDBOX_ROOT):
        return f"ERROR: path {path!r} is outside the workspace ({_SANDBOX_ROOT})"
    return candidate


def read_file(path: str) -> str:
    """Read a file in the workspace and return its contents as a string.

    Args:
        path: File path relative to the workspace directory. Must not escape
            the workspace (no absolute paths outside, no traversal).

    Returns:
        The file's contents, or a string starting with "ERROR:" on failure.
    """
    resolved = _resolve(path)
    if isinstance(resolved, str):
        return resolved
    if not resolved.exists():
        return f"ERROR: {path!r} does not exist"
    if not resolved.is_file():
        return f"ERROR: {path!r} is not a file"
    try:
        return resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"ERROR: {path!r} is not a UTF-8 text file"


def list_files(path: str = ".") -> list[str]:
    """List entries in a directory relative to the workspace.

    Args:
        path: Directory path relative to the workspace. Defaults to ".".

    Returns:
        A sorted list of entries. Directories end with "/". Returns a
        single-element list starting with "ERROR:" on failure.
    """
    resolved = _resolve(path)
    if isinstance(resolved, str):
        return [resolved]
    if not resolved.exists():
        return [f"ERROR: {path!r} does not exist"]
    if not resolved.is_dir():
        return [f"ERROR: {path!r} is not a directory"]
    entries = []
    for child in sorted(resolved.iterdir()):
        if child.name in {"__pycache__", ".venv", ".git", ".pytest_cache"}:
            continue
        entries.append(child.name + ("/" if child.is_dir() else ""))
    return entries


def edit_file(path: str, old_str: str, new_str: str) -> str:
    """Replace ``old_str`` with ``new_str`` in a file. Requires exactly one match.

    To create a NEW file, pass an empty string ("") as old_str and the full file
    contents as new_str.

    The exact-match-once rule protects against accidentally editing multiple
    occurrences. To replace in multiple places, call edit_file once per place
    with enough surrounding context to make old_str unique.

    Args:
        path: File path relative to the workspace.
        old_str: Exact text to find. Must appear exactly once. Empty string
            creates a new file.
        new_str: Text to substitute in.

    Returns:
        "OK: edited {path}" on success, or a string starting with "ERROR:".
    """
    resolved = _resolve(path)
    if isinstance(resolved, str):
        return resolved

    # Empty old_str => create a new file.
    if old_str == "":
        if resolved.exists():
            return f"ERROR: {path!r} already exists; use a non-empty old_str to edit it"
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(new_str, encoding="utf-8")
        return f"OK: created {path}"

    if not resolved.exists():
        return f"ERROR: {path!r} does not exist"
    if not resolved.is_file():
        return f"ERROR: {path!r} is not a file"
    try:
        content = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"ERROR: {path!r} is not a UTF-8 text file"

    count = content.count(old_str)
    if count == 0:
        return f"ERROR: old_str not found in {path!r}"
    if count > 1:
        return (
            f"ERROR: old_str appears {count} times in {path!r}; must be unique. "
            "Add more surrounding context to old_str so it matches exactly once."
        )
    resolved.write_text(content.replace(old_str, new_str), encoding="utf-8")
    return f"OK: edited {path}"


TOOLS = [read_file, list_files, edit_file]
"""The three tools, as a list. Pass this to Gemini's ``tools=`` config."""
