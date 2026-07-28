"""The tools the agent can call. Module 11 end state.

Three tools: `read_file`, `list_files`, `edit_file`. Phase 2 refinements
applied: `list_files`'s description was rewritten with a usage example
(Step 8), and `read_file` raises a structured `ToolError` with a recovery
suggestion (Step 9). See NOTES.md for the before/after.

(Module 13 adds a fourth tool, `search_docs`, over the Chroma corpus.
Module 18 converts `edit_file` into a non-mutating `draft_patch`.)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .guardrails import GuardrailViolation, ensure_within


class ToolError(Exception):
    """A tool failure with an actionable recovery suggestion for the LLM."""

    def __init__(self, message: str, suggestion: str | None = None):
        super().__init__(message)
        self.suggestion = suggestion


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    handler: Callable[..., Any]

    def to_gemini_schema(self) -> dict:
        props = {
            name: {k: v for k, v in spec.items() if k != "default"}
            for name, spec in self.input_schema.get("properties", {}).items()
        }
        parameters: dict = {"type": "object", "properties": props}
        if self.input_schema.get("required"):
            parameters["required"] = self.input_schema["required"]
        return {"name": self.name, "description": self.description, "parameters": parameters}


class ToolSet:
    def __init__(self, tools: list[Tool]):
        self._by_name = {t.name: t for t in tools}

    def schemas(self) -> list[dict]:
        return [t.to_gemini_schema() for t in self._by_name.values()]

    def dispatch(self, name: str, args: dict) -> str:
        tool = self._by_name.get(name)
        if tool is None:
            return f"ERROR: unknown tool {name!r}"
        try:
            result = tool.handler(**args)
        except ToolError as exc:
            return f"ERROR: {exc}. {exc.suggestion}" if exc.suggestion else f"ERROR: {exc}"
        except TypeError as exc:
            return f"ERROR: bad arguments to {name}: {exc}"
        except Exception as exc:  # noqa: BLE001
            return f"ERROR: {type(exc).__name__}: {exc}"
        if isinstance(result, str):
            return result
        return json.dumps(result)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def read_file(path: str, *, workspace: Path) -> str:
    """Read a file in the workspace. Raises ToolError with a suggestion
    (Step 9) instead of a bare exception."""
    try:
        target = ensure_within(path, workspace)
    except GuardrailViolation:
        raise ToolError(
            f"path {path!r} escapes the workspace",
            suggestion="Use a path relative to the workspace root.",
        )
    if not target.is_file():
        raise ToolError(
            f"file not found at {path!r}",
            suggestion="Use list_files() to discover available paths.",
        )
    try:
        return target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise ToolError(f"{path!r} is not UTF-8 text")


def list_files(path: str = ".", *, workspace: Path) -> list[str]:
    """List a directory in the workspace."""
    target = ensure_within(path, workspace)
    if not target.is_dir():
        raise NotADirectoryError(path)
    return sorted(c.name + ("/" if c.is_dir() else "") for c in target.iterdir())


def edit_file(path: str, old_str: str, new_str: str, *, workspace: Path) -> str:
    """Replace `old_str` with `new_str` in a file. Requires exactly one match."""
    target = ensure_within(path, workspace)
    if not target.is_file():
        raise FileNotFoundError(path)
    content = target.read_text(encoding="utf-8")
    count = content.count(old_str)
    if count == 0:
        raise ValueError(f"old_str not found in {path!r}")
    if count > 1:
        raise ValueError(
            f"old_str appears {count} times in {path!r}; must be unique. "
            "Add more surrounding context so it matches exactly once."
        )
    target.write_text(content.replace(old_str, new_str, 1), encoding="utf-8")
    return f"Edited {path!r} (1 replacement)"


def build_toolset(workspace: Path) -> ToolSet:
    return ToolSet(
        [
            Tool(
                name="read_file",
                description=(
                    "Read the contents of a file in the workspace. Paths are "
                    "relative to the workspace root. Returns the file content "
                    "as a string. Example: read_file(path='docs/intro.md')."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": (
                                "Relative path from the workspace root. Forward "
                                "slashes only. Example: 'docs/intro.md'."
                            ),
                        },
                    },
                    "required": ["path"],
                },
                handler=lambda path: read_file(path, workspace=workspace),
            ),
            Tool(
                name="list_files",
                description=(
                    "List the files and subdirectories inside a workspace "
                    "directory. Use when you need to discover what's available "
                    "before reading specific files. Defaults to the workspace "
                    "root if no path is given. Example: list_files(path='docs')."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path from the workspace root. Defaults to '.'.",
                            "default": ".",
                        },
                    },
                },
                handler=lambda path=".": list_files(path, workspace=workspace),
            ),
            Tool(
                name="edit_file",
                description=(
                    "Replace exact text in a file with new text. `old_str` must "
                    "match exactly once in the file — include enough surrounding "
                    "context to make it unique. Use list_files/read_file first to "
                    "confirm the path and current contents."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative path to the file to edit."},
                        "old_str": {
                            "type": "string",
                            "description": "Exact text to replace. Must appear exactly once.",
                        },
                        "new_str": {"type": "string", "description": "Replacement text."},
                    },
                    "required": ["path", "old_str", "new_str"],
                },
                handler=lambda path, old_str, new_str: edit_file(
                    path, old_str, new_str, workspace=workspace
                ),
            ),
        ]
    )
