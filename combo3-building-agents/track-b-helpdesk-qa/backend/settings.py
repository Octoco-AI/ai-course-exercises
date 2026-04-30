"""Centralised config — Track B.

Mirrors track-a-codebase-qa/backend/settings.py with helpdesk-specific
paths (draft_replies, escalations) in place of the codebase's `patches`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    model: str
    workspace_root: Path
    chroma_persist_root: Path
    chroma_collection_name: str
    draft_replies_root: Path
    escalations_root: Path
    max_agent_turns: int


def load_settings() -> Settings:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill in your key."
        )

    workspace = Path(os.environ.get("WORKSPACE_ROOT", "./workspace")).resolve()
    if not workspace.is_dir():
        raise RuntimeError(
            f"Workspace directory not found at {workspace}. "
            f"Run `./scripts/seed-workspace.sh` to populate it."
        )

    chroma_root = Path(
        os.environ.get("CHROMA_PERSIST_ROOT", "../chroma-corpora/track-b-helpdesk/.chroma")
    ).resolve()

    draft_replies = Path(os.environ.get("DRAFT_REPLIES_ROOT", "./draft-replies")).resolve()
    escalations = Path(os.environ.get("ESCALATIONS_ROOT", "./escalations")).resolve()
    draft_replies.mkdir(parents=True, exist_ok=True)
    escalations.mkdir(parents=True, exist_ok=True)

    return Settings(
        anthropic_api_key=api_key,
        # Haiku is usually enough for classify/retrieve/paraphrase helpdesk work.
        model=os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5"),
        workspace_root=workspace,
        chroma_persist_root=chroma_root,
        chroma_collection_name=os.environ.get("CHROMA_COLLECTION_NAME", "track-b-helpdesk"),
        draft_replies_root=draft_replies,
        escalations_root=escalations,
        max_agent_turns=int(os.environ.get("MAX_AGENT_TURNS", "20")),
    )
