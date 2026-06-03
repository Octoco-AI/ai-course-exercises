"""Shared pytest fixtures."""

from __future__ import annotations

from typing import Any

import pytest


class MockLLMClient:
    """Drop-in LLMClient for unit tests. Records calls and returns canned responses."""

    def __init__(self, response: str = '{"category": "Food & Dining", "confidence": 0.9}'):
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt})
        return self.response


@pytest.fixture
def mock_llm():
    """Fresh MockLLMClient per test."""
    return MockLLMClient()
