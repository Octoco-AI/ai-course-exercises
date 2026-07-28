"""Module 3, Step A.3 — the /api/chat endpoint.

Skips at module level until `ChatRequest` (and the route it backs) exist on
`backend.server` — that's the expected state through Module 1/2.

Run just these with: pytest -m m3 tests/m3/test_api.py
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend import server as server_module

if not hasattr(server_module, "ChatRequest"):
    pytest.skip(
        "POST /api/chat not implemented yet — Module 3, Step A.3.",
        allow_module_level=True,
    )

pytestmark = pytest.mark.m3


def test_chat_returns_sse_even_on_misconfiguration(monkeypatch):
    """If the server can't load settings (e.g. no API key), it streams an
    error event rather than returning a 500 — the user sees the error in
    the chat, not a blank screen."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    server_module._settings = None
    server_module._tools = None

    with TestClient(server_module.app) as client:
        response = client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert "event: error" in body
    assert "ANTHROPIC_API_KEY" in body
