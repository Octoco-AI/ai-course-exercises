"""FastAPI endpoint tests.

Uses FastAPI's TestClient; swaps the real categoriser for a mock via
dependency override. This confirms the HTTP layer wires things together
right — status codes, response shapes, error handling.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from expense_categoriser import api as api_module
from expense_categoriser.api import app
from expense_categoriser.models import CategorisationOut


def _replace_categorise_with(mock_result):
    """Monkey-patch the `categorise` function the API calls."""
    def _mock(description, amount, **kwargs):
        if isinstance(mock_result, Exception):
            raise mock_result
        return mock_result
    api_module.categorise = _mock


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_categories_endpoint():
    with TestClient(app) as client:
        response = client.get("/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert "Food & Dining" in data["categories"]


def test_categorise_endpoint_success(monkeypatch):
    _replace_categorise_with(CategorisationOut(category="Food & Dining", confidence=0.9))
    with TestClient(app) as client:
        response = client.post("/categorise", json={"description": "Whole Foods", "amount": 45.23})
        assert response.status_code == 200
        assert response.json() == {"category": "Food & Dining", "confidence": 0.9, "used_fallback": False}


def test_categorise_endpoint_fallback():
    _replace_categorise_with(CategorisationOut(category="Other", confidence=0.3, used_fallback=True))
    with TestClient(app) as client:
        response = client.post("/categorise", json={"description": "Weird Shop", "amount": 12.0})
        assert response.status_code == 200
        assert response.json()["used_fallback"] is True


def test_categorise_endpoint_rejects_missing_fields():
    with TestClient(app) as client:
        response = client.post("/categorise", json={"description": "only description"})
        assert response.status_code == 422  # Pydantic validation error


def test_categorise_endpoint_handles_contract_violation():
    _replace_categorise_with(ValueError("model returned unknown category 'Snacks'"))
    with TestClient(app) as client:
        response = client.post("/categorise", json={"description": "x", "amount": 1.0})
        assert response.status_code == 502
        assert "Snacks" in response.json()["detail"]




def test_top_categories_endpoint():
    # Clear history before test
    api_module.CATEGORY_HISTORY.clear()

    # Populate history with some categories
    _replace_categorise_with(CategorisationOut(category="Food & Dining", confidence=0.9))
    with TestClient(app) as client:
        client.post("/categorise", json={"description": "Restaurant", "amount": 30.0})
        client.post("/categorise", json={"description": "Groceries", "amount": 50.0})

    _replace_categorise_with(CategorisationOut(category="Transportation", confidence=0.8))
    with TestClient(app) as client:
        client.post("/categorise", json={"description": "Gas", "amount": 40.0})
        client.post("/categorise", json={"description": "Bus Ticket", "amount": 5.0})

    _replace_categorise_with(CategorisationOut(category="Food & Dining", confidence=0.95))
    with TestClient(app) as client:
        client.post("/categorise", json={"description": "Cafe", "amount": 15.0})

    with TestClient(app) as client:
        # Test with default k (3)
        response = client.get("/categories/top")
        assert response.status_code == 200
        assert response.json() == {
            "top_categories": [
                {"category": "Food & Dining", "count": 3},
                {"category": "Transportation", "count": 2},
            ]
        }

        # Test with k=1
        response = client.get("/categories/top?k=1")
        assert response.status_code == 200
        assert response.json() == {
            "top_categories": [
                {"category": "Food & Dining", "count": 3},
            ]
        }

        # Test with k=0
        response = client.get("/categories/top?k=0")
        assert response.status_code == 400
        assert response.json() == {"detail": "'k' must be a positive integer."
}
def test_categorise_endpoint_handles_missing_api_key():
    _replace_categorise_with(RuntimeError("GOOGLE_API_KEY is not set"))
    with TestClient(app) as client:
        response = client.post("/categorise", json={"description": "x", "amount": 1.0})
        assert response.status_code == 500
