"""Centralised config loaded from env + defaults. Given — no changes needed.

One place to read environment variables from; the rest of the code reads
from this module. Every field has a default sourced from the environment
(or a hardcoded fallback), so a bare `Settings()` — as used in Module 11's
verification snippets — works out of the box without any extra wiring.
`load_settings()` is the *validated* entry point `server.py` uses: same
defaults, but raises a clear `RuntimeError` if something required (an API
key, the workspace directory) is actually missing.

Provider: the agent runs on **Gemini by default** (the key Octoco provides
for the workshop). Set ANTHROPIC_API_KEY instead of GOOGLE_API_KEY — or
LLM_PROVIDER=anthropic — to build on Claude. Both paths implement the same
tool loop; see `agent.py`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_MODELS = {
    "gemini": "gemini-3.1-flash-lite",
    "anthropic": "claude-sonnet-5",
}


def _select_provider(google_key: str, anthropic_key: str) -> str:
    """Pick the LLM provider. Explicit LLM_PROVIDER wins; else Gemini-first."""
    explicit = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if explicit:
        if explicit not in DEFAULT_MODELS:
            raise RuntimeError(
                f"LLM_PROVIDER must be one of {sorted(DEFAULT_MODELS)}, got {explicit!r}."
            )
        return explicit
    # No explicit choice: default to Gemini (the provided key). Only fall
    # back to Anthropic when it's the *only* key present.
    if not google_key and anthropic_key:
        return "anthropic"
    return "gemini"


def _default_provider() -> str:
    return _select_provider(
        os.environ.get("GOOGLE_API_KEY", "").strip(),
        os.environ.get("ANTHROPIC_API_KEY", "").strip(),
    )


@dataclass(frozen=True)
class Settings:
    provider: str = field(default_factory=_default_provider)
    google_api_key: str = field(default_factory=lambda: os.environ.get("GOOGLE_API_KEY", "").strip())
    anthropic_api_key: str = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", "").strip()
    )
    model: str = ""  # resolved in __post_init__ if left blank
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

    def __post_init__(self) -> None:
        if not self.model:
            override = (
                os.environ.get("GEMINI_MODEL" if self.provider == "gemini" else "ANTHROPIC_MODEL")
                or os.environ.get("MODEL")
                or ""
            ).strip()
            object.__setattr__(self, "model", override or DEFAULT_MODELS[self.provider])


def load_settings() -> Settings:
    """Read env + validate. Raises RuntimeError if required values are missing."""
    settings = Settings()

    if settings.provider == "gemini" and not settings.google_api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Copy .env.example to .env and paste your "
            "Gemini key. (Prefer Claude? Set ANTHROPIC_API_KEY and LLM_PROVIDER=anthropic.)"
        )
    if settings.provider == "anthropic" and not settings.anthropic_api_key:
        raise RuntimeError(
            "LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set. Set the key, "
            "or use the default Gemini path with GOOGLE_API_KEY."
        )
    if not settings.workspace_root.is_dir():
        raise RuntimeError(
            f"Workspace directory not found at {settings.workspace_root}. "
            f"Run `./scripts/seed-workspace.sh` to populate it."
        )

    settings.patches_root.mkdir(parents=True, exist_ok=True)
    return settings
