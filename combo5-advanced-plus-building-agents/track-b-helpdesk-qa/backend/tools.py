"""The tools the helpdesk agent can call.

Module 11 has you build three: `list_tickets`, `read_ticket`, `draft_reply`.
(Module 13 adds a fourth, `search_kb`, over the Chroma KB corpus. Module 18
adds `escalate_to_human` plus an action-gate pattern for it. Neither
exists yet — don't add them now.)

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
            returning (`json` is already imported above).
        """
        # TODO: Step 3 — implement dispatch. See concept.adoc's
        #       "Errors as strings" section for the exact shape.
        raise NotImplementedError("Implement ToolSet.dispatch for step 3.")


# ---------------------------------------------------------------------------
# Handlers — Track B: list_tickets, read_ticket, draft_reply.
#
# Tickets live as one Markdown file per ticket under `workspace/tickets/`,
# named `<ticket_id>.md` (e.g. `TKT-1001.md`), with a small header:
#
#   Status: open
#   Customer: alice@example.com
#   Theme: billing
#
#   ## Message
#
#   <the customer's message>
# ---------------------------------------------------------------------------


# -----------------------------------------------------------------------
# STEP 3a — implement list_tickets
# -----------------------------------------------------------------------
def list_tickets(*, workspace: Path) -> list[str]:
    """List all tickets under workspace/tickets/ as short summary strings.

    Hints:
      - The tickets directory is `workspace / "tickets"`.
      - For each `*.md` file, parse the `Status:` and `Theme:` header
        lines (simple line-by-line text parsing — no need for a YAML
        parser) and return something like `"TKT-1001 [open] billing"`.
      - Sort by ticket id (the filename stem) so results are stable.
    """
    # TODO: Step 3a — implement list_tickets.
    raise NotImplementedError("Implement list_tickets for step 3a.")


# -----------------------------------------------------------------------
# STEP 3b — implement read_ticket
# -----------------------------------------------------------------------
def read_ticket(ticket_id: str, *, workspace: Path) -> str:
    """Read a ticket's full contents.

    Hints:
      - `ensure_within(f"tickets/{ticket_id}.md", workspace)` (imported
        above) resolves the path and raises `GuardrailViolation` if it
        escapes the sandbox — let it raise; `dispatch()`'s generic
        `except Exception` will format it.
      - Check the resolved path exists and is a file; raise
        `FileNotFoundError(ticket_id)` otherwise.
      - Read as UTF-8 text and return the string.
    """
    # TODO: Step 3b — implement read_ticket.
    raise NotImplementedError("Implement read_ticket for step 3b.")


# -----------------------------------------------------------------------
# STEP 3c — implement draft_reply
# -----------------------------------------------------------------------
def draft_reply(ticket_id: str, body: str, *, draft_replies: Path) -> str:
    """Draft a reply to a ticket. Writes to draft_replies/, never mutates
    the ticket itself — a human reviews and sends the reply.

    Hints:
      - Validate `body` isn't empty; raise `ValueError` otherwise.
      - Write to `draft_replies / f"{ticket_id}.md"` (draft_replies is
        created if missing — see `build_toolset`).
      - Return a message confirming the draft was written and that a
        human will review it, e.g. `f"OK: draft reply written for
        {ticket_id}. A human will review and send."`.
    """
    # TODO: Step 3c — implement draft_reply.
    raise NotImplementedError("Implement draft_reply for step 3c.")


# ---------------------------------------------------------------------------
# STEP 3d — build_toolset
# ---------------------------------------------------------------------------
def build_toolset(workspace: Path, *, draft_replies: Path | None = None) -> ToolSet:
    """Wrap the three handlers into a ToolSet bound to `workspace` (and a
    draft-replies output directory, defaulting to `workspace.parent /
    "draft-replies"` if not given).

    Hints:
      - Each `Tool.handler` must be a zero-argument-shape callable from the
        LLM's point of view — bind `workspace` / `draft_replies` via a
        `lambda **kw: read_ticket(**kw, workspace=workspace)`-style closure,
        so the model never has to supply them.
      - Descriptions: rough is fine for now (Phase 2, Step 8 asks you to
        tighten the thinnest one).
      - `input_schema` is JSON-schema `{"type": "object", "properties": {...},
        "required": [...]}` — see the concept doc's example for `read_file`
        (same shape, different fields).
    """
    # TODO: Step 3d — build the three Tool(...) entries and return
    #       ToolSet([...]).
    raise NotImplementedError("Implement build_toolset for step 3d.")
