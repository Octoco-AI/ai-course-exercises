"""Three file-system tools the agent can call.

You are going to write these three tool functions:

  - read_file(path)
  - list_files(path=".")
  - edit_file(path, old_str, new_str)

Docstrings and type hints matter. The Gemini SDK turns them into the JSON schema
the model sees. Keep them clear — the model reads them.

Safety model: every path must be resolved against the current working directory
and rejected if it escapes. Return errors as strings starting with "ERROR:",
don't raise — the LLM reads the message and self-corrects, a stack trace just
confuses it.

Pair the top-of-file `_resolve` helper with whichever exercise step you're on.
"""

from __future__ import annotations

from pathlib import Path

_SANDBOX_ROOT = Path.cwd().resolve()


def _resolve(path: str) -> Path | str:
    """Resolve ``path`` against the sandbox root, or return an error string.

    This helper is given to you — it does the path-safety check so you can
    focus on the tool logic.
    """
    try:
        candidate = (_SANDBOX_ROOT / path).resolve()
    except (OSError, RuntimeError) as exc:
        return f"ERROR: could not resolve path {path!r}: {exc}"
    if not candidate.is_relative_to(_SANDBOX_ROOT):
        return f"ERROR: path {path!r} is outside the sandbox ({_SANDBOX_ROOT})"
    return candidate


# -----------------------------------------------------------------------------
# STEP 2a — implement read_file
# -----------------------------------------------------------------------------
def read_file(path: str) -> str:
    """Read a file in the current working directory and return its contents as a string.

    Args:
        path: File path relative to the working directory.

    Returns:
        The file's contents, or a string starting with "ERROR:" on failure.
    """
    # TODO: call _resolve(path). If it returns a str (error), return it.
    # TODO: check the resolved path exists and is a file.
    # TODO: read the file as UTF-8 text and return the string.
    #       On UnicodeDecodeError, return an informative ERROR string.
    raise NotImplementedError("Implement read_file for step 2a.")


# -----------------------------------------------------------------------------
# STEP 2b — implement list_files
# -----------------------------------------------------------------------------
def list_files(path: str = ".") -> list[str]:
    """List entries in a directory relative to the working directory.

    Args:
        path: Directory path relative to the working directory. Defaults to ".".

    Returns:
        A sorted list of entries. Directories should end with "/". On failure,
        return a single-element list whose first element starts with "ERROR:".
    """
    # TODO: resolve + validate (exists, is_dir).
    # TODO: iterate entries, append "/" to directory names, sort, return.
    raise NotImplementedError("Implement list_files for step 2b.")


# -----------------------------------------------------------------------------
# STEP 2c — implement edit_file
# -----------------------------------------------------------------------------
def edit_file(path: str, old_str: str, new_str: str) -> str:
    """Replace ``old_str`` with ``new_str`` in a file. Requires exactly one match.

    The exact-match-once rule protects against accidentally editing multiple
    occurrences when you only meant one.

    Args:
        path: File path relative to the working directory.
        old_str: Exact text to find. Must appear exactly once in the file.
        new_str: Text to substitute in.

    Returns:
        "OK: edited {path}" on success, or a string starting with "ERROR:".
    """
    # TODO: resolve + validate (exists, is_file).
    # TODO: read the current content.
    # TODO: count occurrences of old_str; error if 0 or > 1.
    # TODO: write the replaced content and return an OK message.
    raise NotImplementedError("Implement edit_file for step 2c.")


# The list of tool callables passed to Gemini. Once you've implemented all
# three, no further changes needed here — the SDK auto-generates JSON schemas
# from your type hints and docstrings.
TOOLS = [read_file, list_files, edit_file]
