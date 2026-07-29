"""The tools the helpdesk agent can call. Module 1 end state.

Three tools: `list_tickets`, `read_ticket`, `draft_reply`. Descriptions
are rough — Module 2 tightens the thinnest one and adds a structured
`ToolError` recovery path.

(Module 4 adds a fourth tool, `search_kb`, over the Chroma KB corpus.
Module 9 adds `escalate_to_human` plus an action-gate pattern for it.)
"""

from __future__ import annotations

import json
import time
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


def _ticket_path(ticket_id: str, workspace: Path) -> Path:
    return ensure_within(f"tickets/{ticket_id}.md", workspace)


def list_tickets(*, workspace: Path) -> list[str]:
    """List all tickets under workspace/tickets/ as short summaries."""
    tickets_dir = workspace / "tickets"
    if not tickets_dir.is_dir():
        return []

    summaries = []
    for path in sorted(tickets_dir.glob("*.md")):
        status, theme = "unknown", "unknown"
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("Status:"):
                status = line.split(":", 1)[1].strip()
            elif line.startswith("Theme:"):
                theme = line.split(":", 1)[1].strip()
        summaries.append(f"{path.stem} [{status}] {theme}")
    return summaries


def read_ticket(ticket_id: str, *, workspace: Path) -> str:
    """Read a ticket's full contents."""
    target = _ticket_path(ticket_id, workspace)
    if not target.is_file():
        raise FileNotFoundError(ticket_id)
    return target.read_text(encoding="utf-8")


def draft_reply(ticket_id: str, body: str, *, draft_replies: Path) -> str:
    """Draft a reply to a ticket. Writes to draft_replies/, never mutates
    the ticket itself."""
    if not body.strip():
        raise ValueError("body is empty")
    draft_replies.mkdir(parents=True, exist_ok=True)
    timestamp = int(time.time() * 1000)
    path = draft_replies / f"{ticket_id}__{timestamp}.md"
    path.write_text(body.rstrip() + "\n", encoding="utf-8")
    return f"OK: draft reply written for {ticket_id} ({path.name}). A human will review and send."


def build_toolset(workspace: Path, *, draft_replies: Path | None = None) -> ToolSet:
    draft_replies = draft_replies or (workspace.parent / "draft-replies")
    return ToolSet(
        [
            Tool(
                name="list_tickets",
                description=(
                    "List all support tickets with their status and theme. Use this "
                    "first to see what's open. Example: list_tickets()."
                ),
                input_schema={"type": "object", "properties": {}},
                handler=lambda: list_tickets(workspace=workspace),
            ),
            Tool(
                name="read_ticket",
                description=(
                    "Read the full contents of a ticket by its id (e.g. 'TKT-1001'). "
                    "Use after list_tickets to look at a specific one. "
                    "Example: read_ticket(ticket_id='TKT-1001')."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "ticket_id": {"type": "string", "description": "Ticket id, e.g. 'TKT-1001'."},
                    },
                    "required": ["ticket_id"],
                },
                handler=lambda ticket_id: read_ticket(ticket_id, workspace=workspace),
            ),
            Tool(
                name="draft_reply",
                description=(
                    "Draft a reply to a ticket for a human to review and send. Never "
                    "sends anything itself."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "ticket_id": {"type": "string", "description": "Ticket id to reply to."},
                        "body": {"type": "string", "description": "Full reply body."},
                    },
                    "required": ["ticket_id", "body"],
                },
                handler=lambda ticket_id, body: draft_reply(
                    ticket_id, body, draft_replies=draft_replies
                ),
            ),
        ]
    )
