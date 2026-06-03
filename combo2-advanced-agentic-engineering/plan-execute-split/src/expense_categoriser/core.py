"""The categorisation logic.

Deliberately pulls apart the pieces that matter for three-layer testing:

  - `build_prompt`                → pure function, unit-test with exact assertions.
  - `parse_response`              → pure function, unit-test.
  - `apply_confidence_threshold`  → pure function, unit-test.
  - `categorise` (the top-level)  → calls Gemini; integration-test with a real
                                    key; mock at the LLM boundary for unit tests.

Herman's blog "Testing the Untestable" says: test the deterministic parts
traditionally, test the AI boundary for contract conformance, and measure
the AI itself via evals at scale.

This module is the code under test for all three layers.
"""

from __future__ import annotations

import json
import os
from typing import Protocol

from .models import CANONICAL_CATEGORIES, CategorisationOut, ModelResponse


SYSTEM_PROMPT = """You are an expense-categorisation assistant for a personal finance app.

Given a transaction description and amount, pick the single best category from this list:

{categories}

Respond with a JSON object of exactly this shape:

  {{"category": "<one of the categories above>", "confidence": <0.0-1.0>}}

Rules:
- Use only categories from the list above. No new categories.
- "confidence" is your self-reported certainty. Use 0.9+ for obvious matches
  (grocery store → Food & Dining), 0.5-0.7 for ambiguous cases, below 0.5
  for genuinely unclear items.
- Do not explain. Do not add extra keys. Respond with JSON only.
"""


def build_prompt(description: str, amount: float) -> str:
    """Build the user-turn prompt. Unit-tested for construction correctness."""
    return f'Transaction: "{description}"\nAmount: {amount:.2f}'


def build_system_prompt(categories: tuple[str, ...] = CANONICAL_CATEGORIES) -> str:
    """Render the system prompt with the canonical category list."""
    joined = "\n".join(f"  - {c}" for c in categories)
    return SYSTEM_PROMPT.format(categories=joined)


def parse_response(raw: str, valid_categories: tuple[str, ...] = CANONICAL_CATEGORIES) -> ModelResponse:
    """Parse and validate the model's JSON output.

    Raises ValueError on malformed JSON, unknown category, or out-of-range
    confidence. The caller decides how to handle that (HTTP 502? Fallback to
    "Other"? Depends on product policy).
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"model response is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"model response must be a JSON object, got {type(data).__name__}")

    try:
        category = data["category"]
        confidence = float(data["confidence"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"model response is missing required fields: {exc}") from exc

    if category not in valid_categories:
        raise ValueError(
            f"model returned unknown category {category!r}; "
            f"expected one of {list(valid_categories)}"
        )

    if not 0.0 <= confidence <= 1.0:
        raise ValueError(f"confidence must be in [0, 1], got {confidence}")

    return ModelResponse(category=category, confidence=confidence)


def apply_confidence_threshold(
    response: ModelResponse,
    threshold: float,
    fallback_category: str = "Other",
) -> CategorisationOut:
    """Graceful degradation: if confidence is below threshold, return the
    fallback category instead of the model's (uncertain) answer.

    From Herman's blog: `if confidence < threshold: show 'popular in similar
    situations'`. For expense categorisation, the analogue is 'Other', which
    the user can manually re-classify.
    """
    if response.confidence < threshold:
        return CategorisationOut(
            category=fallback_category,
            confidence=response.confidence,
            used_fallback=True,
        )
    return CategorisationOut(
        category=response.category,
        confidence=response.confidence,
        used_fallback=False,
    )


# ---- The LLM-facing layer ---------------------------------------------------


class LLMClient(Protocol):
    """Narrow protocol so tests can substitute a mock without touching Gemini."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return the raw JSON string the model produced."""
        ...


class GeminiClient:
    """Thin wrapper around google-genai. Keeps the client instance module-level
    so repeated requests reuse the HTTP connection. Constructed lazily so
    unit tests that never call .generate() don't need a key.
    """

    def __init__(self, *, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        self._model = model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        self._client = None  # lazy

    def _ensure_client(self):
        if self._client is None:
            if not self._api_key:
                raise RuntimeError(
                    "GOOGLE_API_KEY is not set. Either add it to .env or pass api_key explicitly."
                )
            from google import genai
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        from google.genai import types

        client = self._ensure_client()
        response = client.models.generate_content(
            model=self._model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                temperature=0.1,  # classification; we want near-determinism
            ),
        )
        return response.text or ""


# ---- Top-level entrypoint ---------------------------------------------------


def categorise(
    description: str,
    amount: float,
    *,
    client: LLMClient | None = None,
    confidence_threshold: float | None = None,
) -> CategorisationOut:
    """Categorise a single expense. The function three-layer-tested above.

    Args:
        description: The transaction description.
        amount: The transaction amount.
        client: Any LLMClient. Defaults to GeminiClient reading env config.
        confidence_threshold: Below this, fall back to "Other". Defaults to
            env var CONFIDENCE_THRESHOLD or 0.6.
    """
    if client is None:
        client = GeminiClient()

    if confidence_threshold is None:
        confidence_threshold = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.6"))

    system_prompt = build_system_prompt()
    user_prompt = build_prompt(description, amount)

    raw = client.generate(system_prompt, user_prompt)
    parsed = parse_response(raw)
    return apply_confidence_threshold(parsed, threshold=confidence_threshold)
