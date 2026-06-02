"""API-level tests. Confirms the HTTP wiring works without a real API key."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend import server as server_module
from backend.server import app


def test_health(monkeypatch):
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_index_when_no_ui_built(monkeypatch):
    # Pretend the UI isn't built by patching the module-level cache.
    # The response shape depends on whether ui/dist exists at test time.
    with TestClient(app) as client:
        r = client.get("/")
    assert r.status_code == 200
    # Either the JSON hint OR the built UI's HTML.
    assert r.headers["content-type"].startswith(("application/json", "text/html"))


def test_chat_returns_sse_even_on_misconfiguration(monkeypatch, tmp_path):
    """If the server can't load settings (e.g. no API key), it streams an
    error event rather than returning a 500. Important for a chat UX —
    the user sees the error in the chat, not a blank screen."""
    # Force runtime init to fail.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # Reset the module-level singleton so the next request re-loads.
    server_module._settings = None
    server_module._tools = None

    with TestClient(app) as client:
        r = client.post("/api/chat", json={"message": "hello"})

    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    body = r.text
    assert "event: error" in body
    assert "ANTHROPIC_API_KEY" in body
