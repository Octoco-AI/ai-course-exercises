"""Unit tests for the pure functions.

Demonstrates the first testing layer from Herman's "Testing the Untestable":
test the deterministic parts traditionally, and test AI boundaries for
contract conformance (not exact match).
"""

from __future__ import annotations

import pytest

from expense_categoriser.core import (
    apply_confidence_threshold,
    build_prompt,
    build_system_prompt,
    categorise,
    parse_response,
)
from expense_categoriser.models import CANONICAL_CATEGORIES, ModelResponse


# ---- build_prompt ---------------------------------------------------------


def test_build_prompt_includes_description_and_amount():
    prompt = build_prompt("Starbucks Coffee", 5.45)
    assert "Starbucks Coffee" in prompt
    assert "5.45" in prompt


def test_build_prompt_formats_amount_to_two_decimals():
    assert "10.00" in build_prompt("x", 10)
    assert "10.50" in build_prompt("x", 10.5)


def test_build_system_prompt_contains_all_categories():
    sys = build_system_prompt()
    for cat in CANONICAL_CATEGORIES:
        assert cat in sys


# ---- parse_response: the AI-boundary contract -----------------------------
#
# We don't test that the model picked the RIGHT category here — that's the
# eval suite's job. We test that our parser enforces the CONTRACT with the
# model: valid JSON, known category, in-range confidence.


def test_parse_response_happy_path():
    result = parse_response('{"category": "Food & Dining", "confidence": 0.9}')
    assert result.category == "Food & Dining"
    assert result.confidence == 0.9


def test_parse_response_rejects_malformed_json():
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_response("this is not json")


def test_parse_response_rejects_non_object_json():
    with pytest.raises(ValueError, match="must be a JSON object"):
        parse_response('"just a string"')


def test_parse_response_rejects_missing_fields():
    with pytest.raises(ValueError, match="missing required fields"):
        parse_response('{"category": "Food & Dining"}')


def test_parse_response_rejects_unknown_category():
    with pytest.raises(ValueError, match="unknown category"):
        parse_response('{"category": "Snacks", "confidence": 0.9}')


def test_parse_response_rejects_out_of_range_confidence():
    with pytest.raises(ValueError, match="confidence must be in"):
        parse_response('{"category": "Food & Dining", "confidence": 1.5}')


# ---- apply_confidence_threshold: graceful degradation ---------------------


def test_confidence_threshold_above():
    resp = ModelResponse(category="Food & Dining", confidence=0.9)
    out = apply_confidence_threshold(resp, threshold=0.6)
    assert out.category == "Food & Dining"
    assert out.used_fallback is False


def test_confidence_threshold_below_falls_back():
    resp = ModelResponse(category="Shopping", confidence=0.3)
    out = apply_confidence_threshold(resp, threshold=0.6)
    assert out.category == "Other"
    assert out.used_fallback is True
    # Confidence is preserved even in the fallback — callers may want to log it.
    assert out.confidence == 0.3


def test_confidence_threshold_at_boundary():
    # Equal to threshold is NOT considered low-confidence (policy choice).
    resp = ModelResponse(category="Shopping", confidence=0.6)
    out = apply_confidence_threshold(resp, threshold=0.6)
    assert out.category == "Shopping"
    assert out.used_fallback is False


# ---- End-to-end with a mock LLM -------------------------------------------
#
# Herman's blog calls this the "integration test" layer — real pipeline,
# mocked AI. Same seam you'd use for unit tests of any consumer of the
# categoriser.


def test_categorise_e2e_with_mock(mock_llm):
    mock_llm.response = '{"category": "Food & Dining", "confidence": 0.88}'
    result = categorise("Whole Foods", 45.23, client=mock_llm, confidence_threshold=0.6)
    assert result.category == "Food & Dining"
    assert result.confidence == 0.88
    assert result.used_fallback is False
    # Contract: exactly one call was made, and both prompts were non-empty.
    assert len(mock_llm.calls) == 1
    call = mock_llm.calls[0]
    assert "Whole Foods" in call["user_prompt"]
    assert "Food & Dining" in call["system_prompt"]


def test_categorise_with_low_confidence_falls_back(mock_llm):
    mock_llm.response = '{"category": "Shopping", "confidence": 0.4}'
    result = categorise("Weird Corner Shop", 12.99, client=mock_llm, confidence_threshold=0.6)
    assert result.category == "Other"
    assert result.used_fallback is True


def test_categorise_surfaces_contract_violations(mock_llm):
    mock_llm.response = "not json"
    with pytest.raises(ValueError):
        categorise("Anything", 1.0, client=mock_llm)
