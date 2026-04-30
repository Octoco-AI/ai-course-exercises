"""The four tools the agent can call.

Pattern: each tool is a plain function that returns a string (or structured
result). Errors come back as "ERROR: ..." strings so the LLM can self-
correct, not exceptions.

Four tools:

  - search_docs(query)                     — retrieve from the Chroma corpus
  - read_file(path)                        — read from the workspace
  - list_files(path=".")                   — list workspace contents
  - draft_patch(path, old_str, new_str)    — STUBBED PR: writes a unified-diff
                                              file to patches/; does NOT
                                              modify the workspace

This is deliberately a read-plus-draft agent. No delete. No shell. No network.
See `guardrails.py` for the policy.
"""

from __future__ import annotations

import difflib
import time
from pathlib import Path
from typing import TypedDict

import chromadb

from .guardrails import GuardrailViolation, ensure_within


# ---------------------------------------------------------------------------
# Shape of a search result. Mirrors chroma-corpora/shared/search.py so the
# agent-facing contract is identical.
# ---------------------------------------------------------------------------


class SearchHit(TypedDict):
    text: str
    source: str
    heading: str
    score: float


# ---------------------------------------------------------------------------
# Tool implementations. Construct these via ToolSet.from_settings(), which
# binds the sandbox paths once at startup instead of re-reading env per call.
# ---------------------------------------------------------------------------


class ToolSet:
    def __init__(
        self,
        *,
        workspace_root: Path,
        chroma_persist_root: Path,
        chroma_collection_name: str,
        patches_root: Path,
    ) -> None:
        self.workspace_root = workspace_root.resolve()
        self.patches_root = patches_root.resolve()

        client = chromadb.PersistentClient(path=str(chroma_persist_root))
        try:
            self.collection = client.get_collection(chroma_collection_name)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"Chroma collection {chroma_collection_name!r} not found at "
                f"{chroma_persist_root}. Build the corpus first: "
                f"`cd ../chroma-corpora/track-a-codebase && python build.py`."
            ) from exc

    # -- search_docs -----------------------------------------------------

    def search_docs(self, query: str, k: int = 5) -> list[SearchHit]:
        """Search the codebase-documentation corpus. Returns up to k hits."""
        if not query.strip():
            return [{"text": "ERROR: empty query", "source": "", "heading": "", "score": 0.0}]

        result = self.collection.query(query_texts=[query], n_results=k)
        docs = result["documents"][0]
        metadatas = result["metadatas"][0]
        distances = result["distances"][0] if result.get("distances") else [None] * len(docs)

        hits: list[SearchHit] = []
        for doc, meta, dist in zip(docs, metadatas, distances):
            score = max(0.0, 1.0 - float(dist) / 2.0) if dist is not None else 0.0
            hits.append({
                "text": doc,
                "source": meta.get("source", ""),
                "heading": meta.get("heading", ""),
                "score": round(score, 3),
            })
        return hits

    # -- read_file -------------------------------------------------------

    def read_file(self, path: str) -> str:
        """Read a file in the workspace."""
        try:
            resolved = ensure_within(path, self.workspace_root)
        except GuardrailViolation as exc:
            return f"ERROR: {exc}"
        if not resolved.exists():
            return f"ERROR: {path!r} does not exist"
        if not resolved.is_file():
            return f"ERROR: {path!r} is not a file"
        try:
            return resolved.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return f"ERROR: {path!r} is not UTF-8 text"

    # -- list_files ------------------------------------------------------

    def list_files(self, path: str = ".") -> list[str]:
        """List a directory in the workspace."""
        try:
            resolved = ensure_within(path, self.workspace_root)
        except GuardrailViolation as exc:
            return [f"ERROR: {exc}"]
        if not resolved.exists():
            return [f"ERROR: {path!r} does not exist"]
        if not resolved.is_dir():
            return [f"ERROR: {path!r} is not a directory"]
        return [c.name + ("/" if c.is_dir() else "") for c in sorted(resolved.iterdir())]

    # -- draft_patch -----------------------------------------------------

    def draft_patch(self, path: str, old_str: str, new_str: str) -> str:
        """Draft a unified-diff patch. Writes to `patches/<timestamp>.patch`.

        The workspace is NEVER modified. This is the "stubbed PR drafting"
        behaviour the Combo 3 M9 guardrails exercise explicitly calls out.
        """
        try:
            resolved = ensure_within(path, self.workspace_root)
        except GuardrailViolation as exc:
            return f"ERROR: {exc}"
        if not resolved.exists():
            return f"ERROR: {path!r} does not exist"
        if not resolved.is_file():
            return f"ERROR: {path!r} is not a file"

        try:
            content = resolved.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return f"ERROR: {path!r} is not UTF-8 text"

        count = content.count(old_str)
        if count == 0:
            return f"ERROR: old_str not found in {path!r}"
        if count > 1:
            return (
                f"ERROR: old_str appears {count} times in {path!r}; must be unique. "
                "Add more surrounding context to old_str so it matches exactly once."
            )

        new_content = content.replace(old_str, new_str)

        diff_lines = list(difflib.unified_diff(
            content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        ))
        patch_text = "".join(diff_lines)

        # Write to patches/ with a safe, unique name.
        timestamp = int(time.time() * 1000)
        safe_path_slug = path.replace("/", "_").replace("\\", "_")
        patch_file = self.patches_root / f"{timestamp}__{safe_path_slug}.patch"
        patch_file.write_text(patch_text, encoding="utf-8")

        return (
            f"OK: drafted patch at {patch_file.name}. "
            f"The workspace was NOT modified. Review the patch and apply with "
            f"`patch -p1 < patches/{patch_file.name}` if you approve."
        )


# ---------------------------------------------------------------------------
# Anthropic tool schemas — what we pass in the `tools=[]` config.
# ---------------------------------------------------------------------------


def anthropic_tool_schemas() -> list[dict]:
    """Return the tool definitions in Anthropic's format."""
    return [
        {
            "name": "search_docs",
            "description": (
                "Search the codebase-documentation corpus with a natural-language "
                "query. Returns up to 5 relevant chunks with their source file, "
                "heading, and a relevance score in [0, 1]. Use this before reading "
                "full files — it'll tell you where to look."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A natural-language query. Phrase it as a question or keywords.",
                    },
                },
                "required": ["query"],
            },
        },
        {
            "name": "read_file",
            "description": (
                "Read a file from the workspace. The workspace is the source "
                "tree for TodoMagic. Paths are relative to the workspace root."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Workspace-relative path (e.g., 'docs/api.md').",
                    },
                },
                "required": ["path"],
            },
        },
        {
            "name": "list_files",
            "description": (
                "List the contents of a directory in the workspace. Directories "
                "end with a '/'. Use '.' for the workspace root."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Workspace-relative path. Defaults to '.'.",
                        "default": ".",
                    },
                },
            },
        },
        {
            "name": "draft_patch",
            "description": (
                "Draft a unified-diff patch that replaces `old_str` with `new_str` "
                "in the file at `path`. THE WORKSPACE IS NOT MODIFIED. The patch is "
                "written to a patches/ directory for human review. old_str MUST "
                "appear exactly once in the file; include enough surrounding context "
                "to make it unique. Use this when the user asks for a change."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Workspace-relative path to the file to patch.",
                    },
                    "old_str": {
                        "type": "string",
                        "description": "Exact text to replace. Must appear exactly once.",
                    },
                    "new_str": {
                        "type": "string",
                        "description": "Replacement text.",
                    },
                },
                "required": ["path", "old_str", "new_str"],
            },
        },
    ]
