"""Centralised config loaded from env + defaults.

One place to read environment variables from; the rest of the code reads
from this module. Makes it easy to override in tests and in Docker.
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
    patches_root: Path
    max_agent_turns: int
    confidence_threshold: float


def load_settings() -> Settings:
    """Read env + apply defaults. Raises RuntimeError if required values are missing."""
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
        os.environ.get("CHROMA_PERSIST_ROOT", "../chroma-corpora/track-a-codebase/.chroma")
    ).resolve()

    patches = Path(os.environ.get("PATCHES_ROOT", "./patches")).resolve()
    patches.mkdir(parents=True, exist_ok=True)

    return Settings(
        anthropic_api_key=api_key,
        model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        workspace_root=workspace,
        chroma_persist_root=chroma_root,
        chroma_collection_name=os.environ.get("CHROMA_COLLECTION_NAME", "track-a-codebase"),
        patches_root=patches,
        max_agent_turns=int(os.environ.get("MAX_AGENT_TURNS", "20")),
        confidence_threshold=float(os.environ.get("CONFIDENCE_THRESHOLD", "0.3")),
    )
