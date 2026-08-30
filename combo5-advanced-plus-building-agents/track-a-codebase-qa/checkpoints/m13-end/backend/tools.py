"""The tools the agent can call. Module 13 end state.

Four tools: `read_file`, `list_files`, `edit_file`, `search_docs`. The
first three are unchanged from Module 11 (see NOTES.md for that history).
`search_docs` is Module 13's addition — a thin wrapper around the
pre-built Chroma index at `../chroma-corpora/track-a-codebase/` (build it
first with `python build.py` from that directory; see the repo README's
Setup section).

`search_docs` follows the same shape as the other three: a plain
function, a `Tool` entry with a JSON schema, and failures surfaced as a
`ToolError` (never a bare exception) so the LLM can self-correct — here,
that means the Chroma index not existing yet.

(Module 18 converts `edit_file` into a non-mutating `draft_patch`.)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import chromadb

from .guardrails import GuardrailViolation, ensure_within
from .settings import Settings


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


def search_docs(
    query: str,
    k: int = 5,
    *,
    chroma_persist_root: Path,
    chroma_collection_name: str,
) -> list[dict]:
    """Search the indexed docs corpus for passages relevant to `query`.

    Talks directly to the pre-built Chroma collection at
    `chroma_persist_root` — no dependency on chroma-corpora's own Python
    package, just the persisted index files it wrote. Raises ToolError
    with a build hint if the index doesn't exist yet.
    """
    try:
        client = chromadb.PersistentClient(path=str(chroma_persist_root))
        collection = client.get_collection(chroma_collection_name)
    except Exception as exc:
        raise ToolError(
            f"Chroma index not available at {chroma_persist_root} ({type(exc).__name__}: {exc})",
            suggestion=f"Build it first: cd {chroma_persist_root.parent} && python build.py",
        )

    result = collection.query(query_texts=[query], n_results=k)
    docs = result["documents"][0]
    metadatas = result["metadatas"][0]
    distances = result["distances"][0] if result.get("distances") else [None] * len(docs)

    hits = []
    for doc, meta, dist in zip(docs, metadatas, distances):
        # Chroma's cosine distance is in [0, 2]; invert + clip so higher =
        # more relevant. A rough heuristic, good enough for ranking.
        score = max(0.0, 1.0 - float(dist) / 2.0) if dist is not None else 0.0
        hits.append(
            {
                "text": doc,
                "source": meta.get("source", ""),
                "heading": meta.get("heading", ""),
                "score": round(score, 3),
            }
        )
    return hits


def build_toolset(
    workspace: Path,
    *,
    chroma_persist_root: Path | None = None,
    chroma_collection_name: str | None = None,
) -> ToolSet:
    if chroma_persist_root is None or chroma_collection_name is None:
        defaults = Settings()
        chroma_persist_root = chroma_persist_root or defaults.chroma_persist_root
        chroma_collection_name = chroma_collection_name or defaults.chroma_collection_name

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
            Tool(
                name="search_docs",
                description=(
                    "Search the project's indexed documentation corpus for "
                    "passages relevant to a natural-language question. Use this "
                    "for conceptual 'how does X work' questions before falling "
                    "back to list_files/read_file. Returns up to k passages, "
                    "each with its source file, heading, and a relevance score "
                    "in [0, 1]. Example: search_docs(query='how does "
                    "authentication work')."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural-language question or topic to search for.",
                        },
                        "k": {
                            "type": "integer",
                            "description": "Number of passages to return. Defaults to 5.",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
                handler=lambda query, k=5: search_docs(
                    query,
                    k,
                    chroma_persist_root=chroma_persist_root,
                    chroma_collection_name=chroma_collection_name,
                ),
            ),
        ]
    )
