"""Centralised config loaded from env + defaults.

One place to read environment variables from; the rest of the code reads
from this module. Makes it easy to override in tests and in Docker.

Provider: the agent runs on **Gemini by default** (the key Octoco provides).
Set ANTHROPIC_API_KEY instead of GOOGLE_API_KEY — or LLM_PROVIDER=anthropic —
to build on Claude. Both paths implement the same streaming tool loop; see
`agent.py`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_MODELS = {
    "gemini": "gemini-3.1-flash-lite",
    "anthropic": "claude-sonnet-5",
}


@dataclass(frozen=True)
class Settings:
    provider: str  # "gemini" (default) | "anthropic"
    google_api_key: str
    anthropic_api_key: str
    model: str
    workspace_root: Path
    chroma_persist_root: Path
    chroma_collection_name: str
    patches_root: Path
    max_agent_turns: int
    confidence_threshold: float


def _select_provider(google_key: str, anthropic_key: str) -> str:
    """Pick the LLM provider. Explicit LLM_PROVIDER wins; else Gemini-first."""
    explicit = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if explicit:
        if explicit not in DEFAULT_MODELS:
            raise RuntimeError(
                f"LLM_PROVIDER must be one of {sorted(DEFAULT_MODELS)}, got {explicit!r}."
            )
        return explicit
    # No explicit choice: default to Gemini (the provided key). Only fall back
    # to Anthropic when it's the *only* key present.
    if not google_key and anthropic_key:
        return "anthropic"
    return "gemini"


def load_settings() -> Settings:
    """Read env + apply defaults. Raises RuntimeError if required values are missing."""
    google_key = os.environ.get("GOOGLE_API_KEY", "").strip()
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    provider = _select_provider(google_key, anthropic_key)

    if provider == "gemini" and not google_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Copy .env.example to .env and paste your "
            "Gemini key. (Prefer Claude? Set ANTHROPIC_API_KEY and LLM_PROVIDER=anthropic.)"
        )
    if provider == "anthropic" and not anthropic_key:
        raise RuntimeError(
            "LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set. Set the key, "
            "or use the default Gemini path with GOOGLE_API_KEY."
        )

    # Model: a provider-specific override, then a generic MODEL, then the default.
    model_override = (
        os.environ.get("GEMINI_MODEL" if provider == "gemini" else "ANTHROPIC_MODEL")
        or os.environ.get("MODEL")
        or ""
    ).strip()
    model = model_override or DEFAULT_MODELS[provider]

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
        provider=provider,
        google_api_key=google_key,
        anthropic_api_key=anthropic_key,
        model=model,
        workspace_root=workspace,
        chroma_persist_root=chroma_root,
        chroma_collection_name=os.environ.get("CHROMA_COLLECTION_NAME", "track-a-codebase"),
        patches_root=patches,
        max_agent_turns=int(os.environ.get("MAX_AGENT_TURNS", "20")),
        confidence_threshold=float(os.environ.get("CONFIDENCE_THRESHOLD", "0.3")),
    )
