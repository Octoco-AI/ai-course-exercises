"""Always-green scaffold checks.

These confirm the *given* plumbing works, independent of whether Module 11
or Module 12 are done yet — imports resolve, `Settings()` constructs with
sane defaults, the guardrail helpers behave, and the server's always-on
`/health` route responds. `./verify.sh` runs this file specifically so it
stays green on a fresh clone; run `pytest -m m11` / `pytest -m m12` for the
module-specific checks.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def test_backend_package_imports():
    import backend.agent  # noqa: F401
    import backend.guardrails  # noqa: F401
    import backend.server  # noqa: F401
    import backend.settings  # noqa: F401
    import backend.tools  # noqa: F401


def test_settings_constructs_with_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    from backend.settings import Settings

    settings = Settings()
    assert settings.provider == "gemini"
    assert settings.max_agent_turns == 10
    assert settings.model  # resolved to a default


def test_health_endpoint():
    from backend.server import app

    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_guardrails_ensure_within_allows_child_paths(tmp_path: Path):
    from backend.guardrails import ensure_within

    (tmp_path / "a").mkdir()
    assert ensure_within("a", tmp_path) == (tmp_path / "a").resolve()


def test_guardrails_ensure_within_rejects_parent_traversal(tmp_path: Path):
    from backend.guardrails import GuardrailViolation, ensure_within

    with pytest.raises(GuardrailViolation, match="outside the sandbox"):
        ensure_within("../secret", tmp_path)


def test_forbidden_actions_blocked():
    from backend.guardrails import FORBIDDEN_ACTIONS, GuardrailViolation, reject_forbidden

    for action in FORBIDDEN_ACTIONS:
        with pytest.raises(GuardrailViolation, match="not permitted"):
            reject_forbidden(action)
