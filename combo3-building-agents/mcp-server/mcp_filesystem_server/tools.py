"""Filesystem tools, identical in shape to Combo 1 M1's tiny-agent/reference/tools.py.

The pedagogical point of Combo 3 M5 is that you can wrap your EXISTING tools
as an MCP server without changing them. Keep the signatures, keep the error-
as-string pattern, keep the sandboxing — then add the MCP decoration layer
on top. That's what `server.py` does.

If you're studying this file in isolation: yes, it's a duplicate of the
tiny-agent tools. That's deliberate. A real project would import the single
canonical implementation; for this workshop we keep each example self-
contained so it runs without the other repos.
"""

from __future__ import annotations

from pathlib import Path


_SANDBOX_ROOT = Path.cwd().resolve()


def _resolve(path: str) -> Path | str:
    try:
        candidate = (_SANDBOX_ROOT / path).resolve()
    except (OSError, RuntimeError) as exc:
        return f"ERROR: could not resolve path {path!r}: {exc}"
    if not candidate.is_relative_to(_SANDBOX_ROOT):
        return f"ERROR: path {path!r} is outside the sandbox ({_SANDBOX_ROOT})"
    return candidate


def read_file(path: str) -> str:
    """Read a file and return its contents as a string.

    Args:
        path: File path relative to the working directory. Must not escape
            the working directory.

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
    return [child.name + ("/" if child.is_dir() else "") for child in sorted(resolved.iterdir())]


def edit_file(path: str, old_str: str, new_str: str) -> str:
    """Replace ``old_str`` with ``new_str`` in a file. Requires exactly one match.

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
