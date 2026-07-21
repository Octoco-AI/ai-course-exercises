"""Three file-system tools the agent can call.

Deliberately mirrors Thorsten Ball's ampcode walkthrough:
https://ampcode.com/how-to-build-an-agent

  - read_file(path)                       — read a file and return its contents
  - list_files(path=".")                  — list entries in a directory
  - edit_file(path, old_str, new_str)     — replace old_str with new_str, exactly once

All three are plain Python functions. Docstrings and type hints are what the
Gemini SDK turns into the JSON schema the model sees. Keep them clear — the
model reads them.

Safety model: every path is resolved against the current working directory
and rejected if it escapes. No `..` traversal. No absolute paths outside the
sandbox. Errors are returned as strings, not raised — the LLM reads the error
message and self-corrects, a stack trace just confuses it.
"""

from __future__ import annotations

from pathlib import Path

# The sandbox root is whatever the agent is started in. Captured once at
# import time so tool calls are stable across the loop.
_SANDBOX_ROOT = Path.cwd().resolve()


def _resolve(path: str) -> Path | str:
    """Resolve ``path`` against the sandbox root, or return an error string."""
    try:
        candidate = (_SANDBOX_ROOT / path).resolve()
    except (OSError, RuntimeError) as exc:
        return f"ERROR: could not resolve path {path!r}: {exc}"
    if not candidate.is_relative_to(_SANDBOX_ROOT):
        return f"ERROR: path {path!r} is outside the sandbox ({_SANDBOX_ROOT})"
    return candidate


def read_file(path: str) -> str:
    """Read a file in the current working directory and return its contents as a string.

    Args:
        path: File path relative to the working directory. Must not escape
            the working directory (no absolute paths outside, no traversal).

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
    """List entries in a directory relative to the working directory.

    Args:
        path: Directory path relative to the working directory. Defaults to ".".

    Returns:
        A sorted list of entries. Directories end with "/". Hidden entries
        (starting with ".") are included but clearly marked. Returns a
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
        name = child.name + ("/" if child.is_dir() else "")
        entries.append(name)
    return entries


def edit_file(path: str, old_str: str, new_str: str) -> str:
    """Replace ``old_str`` with ``new_str`` in a file. Requires exactly one match.

    The exact-match-once rule protects against accidentally editing multiple
    occurrences when you only meant one. If you want to replace in multiple
    places, call edit_file once per place with enough surrounding context to
    make old_str unique.

    Args:
        path: File path relative to the working directory.
        old_str: Exact text to find. Must appear exactly once in the file.
        new_str: Text to substitute in.

    Returns:
        "OK: edited {path}" on success, or a string starting with "ERROR:".
    """
    resolved = _resolve(path)
    if isinstance(resolved, str):
        return resolved
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
