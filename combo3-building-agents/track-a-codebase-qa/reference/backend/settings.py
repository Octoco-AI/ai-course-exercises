"""Centralised config loaded from env + defaults. Given — no changes needed.

One place to read environment variables from; the rest of the code reads
from this module. Every field has a default sourced from the environment
(or a hardcoded fallback), so a bare `Settings()` — as used in Module 1's
verification snippets — works out of the box. `load_settings()` is the
*validated* entry point `server.py` uses: same defaults, but raises a
clear `RuntimeError` if something required (the API key, the workspace
directory) is actually missing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_MODEL = "claude-haiku-4-5"


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
            os.environ.get("CHROMA_PERSIST_ROOT", "../chroma-corpora/track-a-codebase/.chroma")
        ).resolve()
    )
    chroma_collection_name: str = field(
        default_factory=lambda: os.environ.get("CHROMA_COLLECTION_NAME", "track-a-codebase")
    )
    patches_root: Path = field(
        default_factory=lambda: Path(os.environ.get("PATCHES_ROOT", "./patches")).resolve()
    )
    max_agent_turns: int = field(
        default_factory=lambda: int(os.environ.get("MAX_AGENT_TURNS", "10"))
    )
    confidence_threshold: float = field(
        default_factory=lambda: float(os.environ.get("CONFIDENCE_THRESHOLD", "0.3"))
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

    settings.patches_root.mkdir(parents=True, exist_ok=True)
    return settings
