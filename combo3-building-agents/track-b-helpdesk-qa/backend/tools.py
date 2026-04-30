"""The four tools the helpdesk agent can call.

  - search_kb(query)                             — retrieve from the Chroma KB
  - read_article(path)                           — read a full KB article
  - create_draft_reply(subject, body, tags)      — draft a reply email for a human to send
  - escalate_to_human(category, summary, priority) — create an escalation ticket

`create_draft_reply` and `escalate_to_human` both write to files. A human
reads these out-of-band (email client, ticketing system) and acts.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import TypedDict

import chromadb

from .guardrails import GuardrailViolation, ensure_within


VALID_PRIORITIES = ("low", "normal", "high", "urgent")
VALID_ESCALATION_CATEGORIES = (
    "billing",           # > $20 refund, disputed charge
    "account-recovery",  # lost email + 2FA
    "security",          # suspicious activity
    "legal",             # child accounts, press, privacy law
    "bug-report",        # likely affecting multiple users
    "product-complaint", # frustrated tone, needs human empathy
    "other",
)


class SearchHit(TypedDict):
    text: str
    source: str
    heading: str
    score: float


class ToolSet:
    def __init__(
        self,
        *,
        workspace_root: Path,
        chroma_persist_root: Path,
        chroma_collection_name: str,
        draft_replies_root: Path,
        escalations_root: Path,
    ) -> None:
        self.workspace_root = workspace_root.resolve()
        self.draft_replies_root = draft_replies_root.resolve()
        self.escalations_root = escalations_root.resolve()

        client = chromadb.PersistentClient(path=str(chroma_persist_root))
        try:
            self.collection = client.get_collection(chroma_collection_name)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"Chroma collection {chroma_collection_name!r} not found at "
                f"{chroma_persist_root}. Build the corpus first: "
                f"`cd ../chroma-corpora/track-b-helpdesk && python build.py`."
            ) from exc

    # -- search_kb -------------------------------------------------------

    def search_kb(self, query: str, k: int = 5) -> list[SearchHit]:
        """Search the Streakly KB for passages relevant to a question."""
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

    # -- read_article ----------------------------------------------------

    def read_article(self, path: str) -> str:
        """Read a full KB article when a snippet from search_kb isn't enough."""
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

    # -- create_draft_reply ----------------------------------------------

    def create_draft_reply(
        self,
        subject: str,
        body: str,
        tags: list[str] | None = None,
    ) -> str:
        """Draft a reply email for a human to review and send.

        The agent never sends email itself. This writes a Markdown file under
        draft-replies/ which a support human opens, edits if needed, then
        copies into their email client.
        """
        if not subject.strip():
            return "ERROR: subject is empty"
        if not body.strip():
            return "ERROR: body is empty"

        timestamp = int(time.time() * 1000)
        safe_subject = "".join(c if c.isalnum() or c in "-_" else "_" for c in subject)[:50]
        path = self.draft_replies_root / f"{timestamp}__{safe_subject}.md"

        tags = tags or []
        header = [
            "---",
            f"subject: {subject}",
            f"tags: [{', '.join(tags)}]",
            f"drafted_at: {time.strftime('%Y-%m-%dT%H:%M:%S%z', time.gmtime(timestamp / 1000))}",
            "---",
            "",
        ]
        path.write_text("\n".join(header) + body.rstrip() + "\n", encoding="utf-8")
        return (
            f"OK: draft reply written to {path.name}. A human will review and send."
        )

    # -- escalate_to_human -----------------------------------------------

    def escalate_to_human(
        self,
        category: str,
        summary: str,
        priority: str = "normal",
    ) -> str:
        """Create an escalation ticket for a human to pick up.

        Args:
            category: one of the VALID_ESCALATION_CATEGORIES.
            summary: what the user asked, what you tried, and why this needs a human.
            priority: 'low' | 'normal' | 'high' | 'urgent'.
        """
        if category not in VALID_ESCALATION_CATEGORIES:
            return (
                f"ERROR: unknown category {category!r}. Use one of: "
                f"{', '.join(VALID_ESCALATION_CATEGORIES)}"
            )
        if priority not in VALID_PRIORITIES:
            return f"ERROR: priority must be one of {', '.join(VALID_PRIORITIES)}"
        if not summary.strip():
            return "ERROR: summary is empty"

        timestamp = int(time.time() * 1000)
        path = self.escalations_root / f"{timestamp}__{priority}__{category}.md"
        payload = {
            "category": category,
            "priority": priority,
            "summary": summary,
            "escalated_at_ms": timestamp,
        }
        path.write_text(
            "---\n" + "\n".join(f"{k}: {v}" for k, v in payload.items()) + "\n---\n\n" + summary + "\n",
            encoding="utf-8",
        )

        return (
            f"OK: escalation {path.name} filed. A human will be paged according to "
            f"priority={priority}. Tell the user a human will respond."
        )


def anthropic_tool_schemas() -> list[dict]:
    """Tool definitions for the Anthropic API."""
    return [
        {
            "name": "search_kb",
            "description": (
                "Search the Streakly knowledge base for passages relevant to a user's "
                "question. Returns up to 5 chunks with source article and heading. "
                "Use this FIRST for most questions — it's cheap and surfaces the right "
                "article."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural-language query derived from the user's question.",
                    },
                },
                "required": ["query"],
            },
        },
        {
            "name": "read_article",
            "description": (
                "Read a full KB article when a snippet from search_kb isn't enough. "
                "Path is a filename relative to the KB root, e.g. 'billing-and-plans.md'."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Article path, e.g. 'billing-and-plans.md'.",
                    },
                },
                "required": ["path"],
            },
        },
        {
            "name": "create_draft_reply",
            "description": (
                "Draft a reply email for a human support agent to review and send. "
                "YOU NEVER SEND EMAILS YOURSELF. Use this when you have a clear answer "
                "the user needs and the question doesn't require escalation. The draft "
                "is reviewed by a human before going out."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "Email subject line.",
                    },
                    "body": {
                        "type": "string",
                        "description": "Full reply body. Friendly, cite KB articles when relevant.",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Topic tags for routing. e.g. ['billing', 'refund'].",
                        "default": [],
                    },
                },
                "required": ["subject", "body"],
            },
        },
        {
            "name": "escalate_to_human",
            "description": (
                "Create an escalation ticket for a human to handle. Use when: "
                "the question requires looking up specific account data you can't see; "
                "a billing refund over $20; account recovery with no email access; "
                "suspected security issue; legal / press / child-safety concerns; "
                "a product complaint where tone suggests the user needs empathy from a human. "
                "Always prefer escalation over speculating about user-specific details."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": list(VALID_ESCALATION_CATEGORIES),
                        "description": "Escalation category.",
                    },
                    "summary": {
                        "type": "string",
                        "description": (
                            "One paragraph: what the user asked, what you tried, "
                            "and why a human is needed."
                        ),
                    },
                    "priority": {
                        "type": "string",
                        "enum": list(VALID_PRIORITIES),
                        "description": "'urgent' for security/legal; 'high' for account-recovery; 'normal' for most; 'low' for non-blocking.",
                        "default": "normal",
                    },
                },
                "required": ["category", "summary"],
            },
        },
    ]
