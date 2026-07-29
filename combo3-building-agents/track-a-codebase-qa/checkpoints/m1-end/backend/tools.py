"""The tools the agent can call. Module 1 end state.

Three tools: `read_file`, `list_files`, `edit_file`. Descriptions are
rough — Module 2 tightens the thinnest one and adds a structured
`ToolError` recovery path.

(Module 4 adds a fourth tool, `search_docs`, over the Chroma corpus.
Module 9 converts `edit_file` into a non-mutating `draft_patch`.)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .guardrails import ensure_within


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    handler: Callable[..., Any]

    def to_anthropic_schema(self, strict: bool = True) -> dict:
        schema = {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
        if strict:
            schema["strict"] = True
        return schema


class ToolSet:
    def __init__(self, tools: list[Tool]):
        self._by_name = {t.name: t for t in tools}

    def schemas(self, strict: bool = True) -> list[dict]:
        return [t.to_anthropic_schema(strict=strict) for t in self._by_name.values()]

    def dispatch(self, name: str, args: dict) -> str:
        tool = self._by_name.get(name)
        if tool is None:
            return f"ERROR: unknown tool {name!r}"
        try:
            result = tool.handler(**args)
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
    """Read a file inside the workspace. Raises on path outside the workspace."""
    target = ensure_within(path, workspace)
    if not target.is_file():
        raise FileNotFoundError(path)
    return target.read_text()


def list_files(path: str = ".", *, workspace: Path) -> list[str]:
    """List files and directories inside the workspace."""
    target = ensure_within(path, workspace)
    if not target.is_dir():
        raise NotADirectoryError(path)
    return sorted(p.name for p in target.iterdir())


def edit_file(path: str, old_str: str, new_str: str, *, workspace: Path) -> str:
    """Replace a substring in a workspace file. Returns a summary."""
    target = ensure_within(path, workspace)
    if not target.is_file():
        raise FileNotFoundError(path)
    content = target.read_text()
    if old_str not in content:
        raise ValueError(f"old_str not found in {path!r}")
    target.write_text(content.replace(old_str, new_str, 1))
    return f"Edited {path!r} (1 replacement)"


def build_toolset(workspace: Path) -> ToolSet:
    return ToolSet(
        [
            Tool(
                name="read_file",
                description=(
                    "Read the contents of a file in the workspace. "
                    "Paths are relative to the workspace root. "
                    "Returns the file content as a string. "
                    "Example: read_file(path='docs/intro.md')."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path, e.g. 'docs/intro.md'.",
                        },
                    },
                    "required": ["path"],
                },
                handler=lambda path: read_file(path, workspace=workspace),
            ),
            Tool(
                name="list_files",
                description=(
                    "List files and subdirectories inside a workspace directory. "
                    "Path defaults to the workspace root. "
                    "Example: list_files(path='docs')."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative directory path. Defaults to '.'.",
                            "default": ".",
                        },
                    },
                    "required": [],
                },
                handler=lambda path=".": list_files(path, workspace=workspace),
            ),
            Tool(
                name="edit_file",
                description=(
                    "Replace a substring in a workspace file. The substring "
                    "`old_str` must appear exactly once. Returns a summary. "
                    "Example: edit_file(path='foo.py', old_str='def foo():', new_str='def bar():')."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative file path."},
                        "old_str": {"type": "string", "description": "The substring to replace."},
                        "new_str": {"type": "string", "description": "The replacement."},
                    },
                    "required": ["path", "old_str", "new_str"],
                },
                handler=lambda path, old_str, new_str: edit_file(path, old_str, new_str, workspace=workspace),
            ),
        ]
    )
