"""Centralised config loaded from env + defaults. Given — no changes needed.

Mirrors track-a-codebase-qa/backend/settings.py with helpdesk-specific
paths (`draft_replies_root`, `escalations_root`) in place of the
codebase's `patches_root`. Every field has a default sourced from the
environment (or a hardcoded fallback), so a bare `Settings()` — as used in
Module 1's verification snippets — works out of the box.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_MODEL = "claude-haiku-4-5"  # classify/retrieve/paraphrase needs less than Sonnet


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", "").strip()
    )
    model: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL))
    workspace_root: Path = field(
        default_factory=lambda: Path(os.environ.get("WORKSPACE_ROOT", "./workspace")).resolve()
    )
    chroma_persist_root: Path = field(
        default_factory=lambda: Path(
            os.environ.get("CHROMA_PERSIST_ROOT", "../chroma-corpora/track-b-helpdesk/.chroma")
        ).resolve()
    )
    chroma_collection_name: str = field(
        default_factory=lambda: os.environ.get("CHROMA_COLLECTION_NAME", "track-b-helpdesk")
    )
    draft_replies_root: Path = field(
        default_factory=lambda: Path(os.environ.get("DRAFT_REPLIES_ROOT", "./draft-replies")).resolve()
    )
    escalations_root: Path = field(
        default_factory=lambda: Path(os.environ.get("ESCALATIONS_ROOT", "./escalations")).resolve()
    )
    max_agent_turns: int = field(
        default_factory=lambda: int(os.environ.get("MAX_AGENT_TURNS", "10"))
    )


def load_settings() -> Settings:
    """Read env + validate. Raises RuntimeError if required values are missing."""
    settings = Settings()

    if not settings.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill in your key."
        )
    if not settings.workspace_root.is_dir():
        raise RuntimeError(
            f"Workspace directory not found at {settings.workspace_root}. "
            f"Run `./scripts/seed-workspace.sh` to populate it."
        )

    settings.draft_replies_root.mkdir(parents=True, exist_ok=True)
    settings.escalations_root.mkdir(parents=True, exist_ok=True)
    return settings
