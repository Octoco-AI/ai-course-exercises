"""API tests — Track B. Mirror Track A's test_api.py."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend import server as server_module
from backend.server import app


def test_health():
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_index_works_regardless_of_ui_build_state():
    with TestClient(app) as client:
        r = client.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith(("application/json", "text/html"))


def test_chat_streams_error_on_misconfig(monkeypatch):
    """No API key → client sees a structured SSE error event, not a 500."""
    # Remove BOTH provider keys so load_settings raises (default provider is
    # Gemini, so GOOGLE_API_KEY must be gone too).
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    server_module._settings = None
    server_module._tools = None

    with TestClient(app) as client:
        r = client.post("/api/chat", json={"message": "hello"})

    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    assert "event: error" in r.text
    # Default provider is Gemini, so the missing-key error names GOOGLE_API_KEY.
    assert "GOOGLE_API_KEY" in r.text
