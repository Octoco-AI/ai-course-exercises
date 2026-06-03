"""Pydantic schemas + canonical category list."""

from __future__ import annotations

from pydantic import BaseModel, Field


# Keep this list short and stable — the prompt enumerates it. Don't reshuffle
# without re-running the eval baseline; label order can subtly affect the LLM.
CANONICAL_CATEGORIES: tuple[str, ...] = (
    "Food & Dining",
    "Transportation",
    "Shopping",
    "Entertainment",
    "Healthcare",
    "Utilities",
    "Housing",
    "Travel",
    "Personal Care",
    "Subscriptions",
    "Education",
    "Gifts & Donations",
    "Income",
    "Other",
)


class ExpenseIn(BaseModel):
    """What the API caller sends."""

    description: str = Field(..., description="Transaction description as it appears on the statement.", min_length=1, max_length=500)
    amount: float = Field(..., description="Transaction amount in the user's currency. Negative = credit.")


class CategorisationOut(BaseModel):
    """What the API returns."""

    category: str = Field(..., description="The chosen category.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model-reported confidence.")
    used_fallback: bool = Field(False, description="True when the model's confidence fell below the threshold and we returned 'Other' as a fallback.")


class ModelResponse(BaseModel):
    """The schema we ask Gemini to produce. Kept separate from CategorisationOut
    so we can wrap the raw model output with our fallback logic before returning."""

    category: str
    confidence: float = Field(..., ge=0.0, le=1.0)
