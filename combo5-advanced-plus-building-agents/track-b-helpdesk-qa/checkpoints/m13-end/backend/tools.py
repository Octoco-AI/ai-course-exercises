"""The tools the helpdesk agent can call. Module 13 end state.

Four tools: `list_tickets`, `read_ticket`, `draft_reply`, `search_kb`. The
first three are unchanged from Module 11 (see NOTES.md for that history).
`search_kb` is Module 13's addition — a thin wrapper around the pre-built
Chroma index at `../chroma-corpora/track-b-helpdesk/` (build it first with
`python build.py` from that directory; see the repo README's Setup
section).

`search_kb` follows the same shape as the other three: a plain function, a
`Tool` entry with a JSON schema, and failures surfaced as a `ToolError`
(never a bare exception) so the LLM can self-correct — here, that means
the Chroma index not existing yet.

(Module 18 adds `escalate_to_human` plus an action-gate pattern for it.)
"""

from __future__ import annotations

import json
import time
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
    """Read a ticket's full contents. Raises ToolError with a suggestion
    (Step 9) instead of a bare exception."""
    try:
        target = _ticket_path(ticket_id, workspace)
    except GuardrailViolation:
        raise ToolError(
            f"ticket id {ticket_id!r} resolves outside the workspace",
            suggestion="Use a ticket id like 'TKT-1001', with no path separators.",
        )
    if not target.is_file():
        raise ToolError(
            f"no ticket found with id {ticket_id!r}",
            suggestion="Use list_tickets() to see available ticket ids.",
        )
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


def search_kb(
    query: str,
    k: int = 5,
    *,
    chroma_persist_root: Path,
    chroma_collection_name: str,
) -> list[dict]:
    """Search the Streakly help-centre KB for passages relevant to `query`.

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
    draft_replies: Path | None = None,
    chroma_persist_root: Path | None = None,
    chroma_collection_name: str | None = None,
) -> ToolSet:
    draft_replies = draft_replies or (workspace.parent / "draft-replies")
    if chroma_persist_root is None or chroma_collection_name is None:
        defaults = Settings()
        chroma_persist_root = chroma_persist_root or defaults.chroma_persist_root
        chroma_collection_name = chroma_collection_name or defaults.chroma_collection_name

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
                    "Read the full contents of a ticket by its id (e.g. 'TKT-1001'), "
                    "including the customer's message. Use after list_tickets to "
                    "look at a specific one. Example: read_ticket(ticket_id='TKT-1001')."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "ticket_id": {
                            "type": "string",
                            "description": "Ticket id, e.g. 'TKT-1001'.",
                        },
                    },
                    "required": ["ticket_id"],
                },
                handler=lambda ticket_id: read_ticket(ticket_id, workspace=workspace),
            ),
            Tool(
                name="draft_reply",
                description=(
                    "Draft a reply to a ticket for a human to review and send. Never "
                    "sends anything itself. Use once you have a clear answer for the "
                    "customer."
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
            Tool(
                name="search_kb",
                description=(
                    "Search the Streakly help-centre KB for passages relevant to a "
                    "customer's question. Use this before drafting a reply to "
                    "conceptual 'how do I ...' questions. Returns up to k "
                    "passages, each with its source article, heading, and a "
                    "relevance score in [0, 1]. Example: "
                    "search_kb(query='how do I enable 2FA')."
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
                handler=lambda query, k=5: search_kb(
                    query,
                    k,
                    chroma_persist_root=chroma_persist_root,
                    chroma_collection_name=chroma_collection_name,
                ),
            ),
        ]
    )
