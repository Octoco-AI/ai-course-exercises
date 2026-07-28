"""The tools the agent can call.

Module 11 has you build three: `read_file`, `list_files`, `edit_file`.
(Module 13 adds a fourth, `search_docs`, over the Chroma corpus. Module 18
converts `edit_file` into a non-mutating `draft_patch`. Neither exists yet
— don't add them now.)

Pattern: each handler is a plain function; `dispatch()` never lets an
exception escape — it catches everything and returns a string starting
with "ERROR:" so the LLM can self-correct on the next turn, rather than
crashing the loop.

The `Tool` dataclass and `to_gemini_schema()` are given — they're pure
mechanics (see the concept doc's "Typed Tool + ToolSet" section for the
full shape). What you write: `ToolSet.dispatch()`, the three handlers, and
`build_toolset()`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .guardrails import GuardrailViolation, ensure_within


# ---------------------------------------------------------------------------
# Tool + ToolSet — given. Mechanics only; see concept.adoc for the narrative.
# ---------------------------------------------------------------------------


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict  # JSON-schema for the parameters
    handler: Callable[..., Any]

    def to_gemini_schema(self) -> dict:
        # Gemini wants {name, description, parameters}. `parameters` is the
        # same JSON-schema object, minus the keywords its validator
        # rejects — most commonly `default`.
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
        # The `function_declarations` list you pass to types.Tool(...).
        return [t.to_gemini_schema() for t in self._by_name.values()]

    # -----------------------------------------------------------------
    # STEP 3 — implement dispatch
    # -----------------------------------------------------------------
    def dispatch(self, name: str, args: dict) -> str:
        """Call the named tool's handler with `args`. Never raises.

        Hints:
          - Look up the tool in `self._by_name`; unknown name -> return an
            "ERROR: unknown tool {name!r}" string.
          - Call `tool.handler(**args)`.
          - `except TypeError` -> "ERROR: bad arguments to {name}: {exc}"
            (the model passed the wrong shape of arguments).
          - `except Exception` -> "ERROR: {type(exc).__name__}: {exc}"
            (a handler raised — e.g. FileNotFoundError, ValueError).
          - If the result isn't already a string, `json.dumps` it before
            returning (tool results must be strings for the SSE preview
            in Module 12; `json` is already imported above).
        """
        # TODO: Step 3 — implement dispatch. See concept.adoc's
        #       "Errors as strings" section for the exact shape.
        raise NotImplementedError("Implement ToolSet.dispatch for step 3.")


# ---------------------------------------------------------------------------
# Handlers — Track A: read_file, list_files, edit_file.
# ---------------------------------------------------------------------------


# -----------------------------------------------------------------------
# STEP 3a — implement read_file
# -----------------------------------------------------------------------
def read_file(path: str, *, workspace: Path) -> str:
    """Read a file in the workspace.

    Hints:
      - `ensure_within(path, workspace)` (imported above) resolves the path
        and raises `GuardrailViolation` if it escapes the sandbox — let it
        raise; `dispatch()`'s generic `except Exception` will format it.
      - Check the resolved path exists and is a file; raise
        `FileNotFoundError(path)` / a suitable error otherwise.
      - Read as UTF-8 text and return the string. On `UnicodeDecodeError`,
        raise (or return) an informative message — don't let a raw
        traceback reach the model.
    """
    # TODO: Step 3a — implement read_file.
    raise NotImplementedError("Implement read_file for step 3a.")


# -----------------------------------------------------------------------
# STEP 3b — implement list_files
# -----------------------------------------------------------------------
def list_files(path: str = ".", *, workspace: Path) -> list[str]:
    """List a directory in the workspace.

    Hints:
      - `ensure_within(path, workspace)`, then check `.is_dir()`.
      - Return a sorted list of entry names; suffix directory entries
        with "/" so the model can tell files from dirs without another call.
    """
    # TODO: Step 3b — implement list_files.
    raise NotImplementedError("Implement list_files for step 3b.")


# -----------------------------------------------------------------------
# STEP 3c — implement edit_file
# -----------------------------------------------------------------------
def edit_file(path: str, old_str: str, new_str: str, *, workspace: Path) -> str:
    """Replace `old_str` with `new_str` in a file. Requires exactly one match.

    The exact-match-once rule protects against silently editing the wrong
    occurrence when `old_str` isn't unique.

    Hints:
      - `ensure_within` + exists/is_file checks, as in read_file.
      - Read the current content; `content.count(old_str)` — raise
        `ValueError` if it's 0 (not found) or > 1 (not unique; ask for
        more surrounding context in the error message).
      - Write the replaced content back; return
        `f"Edited {path!r} (1 replacement)"`.
    """
    # TODO: Step 3c — implement edit_file.
    raise NotImplementedError("Implement edit_file for step 3c.")


# ---------------------------------------------------------------------------
# STEP 3d — build_toolset
# ---------------------------------------------------------------------------
def build_toolset(workspace: Path) -> ToolSet:
    """Wrap the three handlers into a ToolSet bound to `workspace`.

    Hints:
      - Each `Tool.handler` must be a zero-argument-shape callable from the
        LLM's point of view — i.e. `lambda **kw: read_file(**kw, workspace=workspace)`
        — so `workspace` is bound once here, not passed by the model.
      - Descriptions: rough is fine for now (Phase 2, Step 8 asks you to
        tighten the thinnest one). Keep them short but real — "Read a file
        in the workspace." is enough for Phase 1.
      - `input_schema` is JSON-schema `{"type": "object", "properties": {...},
        "required": [...]}` — see the concept doc's example for `read_file`.
    """
    # TODO: Step 3d — build the three Tool(...) entries and return
    #       ToolSet([...]).
    raise NotImplementedError("Implement build_toolset for step 3d.")
