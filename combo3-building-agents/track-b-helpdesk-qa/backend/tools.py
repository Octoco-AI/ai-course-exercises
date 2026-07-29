"""The tools the helpdesk agent can call.

Module 1 has you build three: `list_tickets`, `read_ticket`, `draft_reply`.
(Module 4 adds a fourth, `search_kb`, over the Chroma KB corpus. Module 9
adds `escalate_to_human` plus an action-gate pattern for it. Neither
exists yet — don't add them now.)

Pattern: each handler is a plain function; `dispatch()` never lets an
exception escape — it catches everything and returns a string starting
with "ERROR:" so the LLM can self-correct on the next turn, rather than
crashing the loop.

The `Tool` dataclass and `to_anthropic_schema()` are given — they're pure
mechanics. What you write: `ToolSet.dispatch()`, the three handlers, and
`build_toolset()`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .guardrails import GuardrailViolation, ensure_within


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

    # -----------------------------------------------------------------
    # STEP 3 — implement dispatch
    # -----------------------------------------------------------------
    def dispatch(self, name: str, args: dict) -> str:
        """Call the named tool's handler with `args`. Never raises.

        Hints:
          - Unknown name -> "ERROR: unknown tool {name!r}".
          - `except TypeError` -> "ERROR: bad arguments to {name}: {exc}".
          - `except Exception` -> "ERROR: {type(exc).__name__}: {exc}".
          - Non-string results -> `json.dumps` before returning.
        """
        # TODO: Step 3 — implement dispatch.
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
        lines and return something like `"TKT-1001 [open] billing"`.
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
        escapes the sandbox — let it raise.
      - Raise `FileNotFoundError(ticket_id)` if the ticket doesn't exist.
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
      - Write to `draft_replies / f"{ticket_id}.md"`.
      - Return a message confirming the draft was written.
    """
    # TODO: Step 3c — implement draft_reply.
    raise NotImplementedError("Implement draft_reply for step 3c.")


# ---------------------------------------------------------------------------
# STEP 3d — build_toolset
# ---------------------------------------------------------------------------
def build_toolset(workspace: Path, *, draft_replies: Path | None = None) -> ToolSet:
    """Wrap the three handlers into a ToolSet bound to `workspace` (and a
    draft-replies output directory).

    Hints:
      - Bind `workspace` / `draft_replies` in each `Tool.handler` via a
        closure, so the model never has to supply them.
      - Descriptions: rough is fine for now (Module 2 asks you to tighten
        the thinnest one).
    """
    # TODO: Step 3d — build the three Tool(...) entries and return
    #       ToolSet([...]).
    raise NotImplementedError("Implement build_toolset for step 3d.")
