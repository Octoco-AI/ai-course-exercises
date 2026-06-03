"""FastAPI app exposing the categoriser.

Run locally:
    expense-api
    # or:
    uvicorn expense_categoriser.api:app --reload

Test:
    curl -X POST http://localhost:8000/categorise \\
         -H "Content-Type: application/json" \\
         -d '{"description": "Whole Foods", "amount": 45.23}'
"""

from __future__ import annotations

import logging
import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

from .core import categorise
from .models import CANONICAL_CATEGORIES, CategorisationOut, ExpenseIn


load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Expense Categoriser",
    version="0.1.0",
    description="Workshop reference: a small FastAPI service that categorises expenses using Gemini.",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@app.get("/categories")
def categories() -> dict[str, list[str]]:
    """Return the canonical category list. Useful for API consumers and tests."""
    return {"categories": list(CANONICAL_CATEGORIES)}


@app.post("/categorise", response_model=CategorisationOut)
def categorise_expense(expense: ExpenseIn) -> CategorisationOut:
    """Categorise a single expense.

    Returns 502 if the LLM returns malformed output (contract violation). The
    confidence-threshold fallback (returning "Other" with used_fallback=True)
    is a SUCCESSFUL response, not an error — the client needs to know the
    model wasn't confident but not that everything failed.
    """
    start = time.perf_counter()
    try:
        result = categorise(expense.description, expense.amount)
    except ValueError as exc:
        # Contract violation from the LLM. Worth logging loudly — this is the
        # "model started misbehaving" signal the CE pipeline watches for.
        logger.warning("Contract violation from LLM: %s", exc)
        raise HTTPException(status_code=502, detail=f"LLM returned unparseable output: {exc}") from exc
    except RuntimeError as exc:
        # Missing API key, etc. — configuration problem.
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "categorised %r -> %s (conf=%.2f, fallback=%s, %.0fms)",
        expense.description, result.category, result.confidence, result.used_fallback, elapsed_ms,
    )
    return result


def dev_main() -> None:
    """Entrypoint for `expense-api` script. Uses uvicorn with reload for local work."""
    import uvicorn

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("expense_categoriser.api:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    dev_main()
