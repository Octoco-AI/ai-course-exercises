"""DeepEval-style eval suite. This is the "third layer" from Herman's blog.

Run locally:
    pytest -m evals tests/evals/

In CI:
    The `.github/workflows/evals.yml` runs this on every PR with the GOOGLE_API_KEY
    secret. A failing eval blocks the merge.

What's being tested:
  1. **Acceptance accuracy** — across the golden dataset, the rate of
     "chose an acceptable category" must be >= ACCURACY_THRESHOLD.
  2. **Zero catastrophics** — no case may be categorised as one of its
     explicitly unacceptable categories. This is a hard gate.
  3. **Latency** — p95 per-request latency below a ceiling.
  4. **Confidence distribution** — most high-confidence predictions should
     actually be correct (rough calibration check).

Costs real money: every case is a Gemini call. Keep the dataset small
(~20 cases) for the fast-feedback CI loop; expand to 100+ for nightly runs.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from statistics import mean, median

import pytest

from expense_categoriser.core import categorise


# ---- thresholds (these are the spec's acceptance criteria turned into CE gates)

ACCURACY_THRESHOLD = 0.85       # ≥ 85% of cases must be acceptable
CATASTROPHIC_THRESHOLD = 0      # ZERO cases may hit an unacceptable category
P95_LATENCY_SECONDS = 3.0       # generous; tighten once we have a baseline
MIN_HIGH_CONF_ACCEPTABLE = 0.90 # of high-conf (>=0.8) predictions, at least 90% acceptable


EVAL_DATASET_PATH = Path(__file__).parent / "eval_dataset.json"


pytestmark = pytest.mark.evals


@pytest.fixture(scope="module")
def eval_dataset() -> list[dict]:
    return json.loads(EVAL_DATASET_PATH.read_text())


@pytest.fixture(scope="module")
def eval_results(eval_dataset):
    """Run every case through the real categoriser, once, and cache the results.

    This is the only expensive step — all four tests below read from the
    same fixture so they share one full pass of the dataset.
    """
    if not os.environ.get("GOOGLE_API_KEY"):
        pytest.skip("GOOGLE_API_KEY not set — eval suite skipped (explicit opt-in required)")

    results = []
    for case in eval_dataset:
        t0 = time.perf_counter()
        try:
            out = categorise(case["description"], case["amount"])
            elapsed = time.perf_counter() - t0
            results.append({
                "case": case,
                "output": out,
                "elapsed": elapsed,
                "error": None,
            })
        except Exception as exc:  # noqa: BLE001 — record and keep going
            results.append({
                "case": case,
                "output": None,
                "elapsed": time.perf_counter() - t0,
                "error": str(exc),
            })
    return results


# ---- the gates --------------------------------------------------------------


def test_accuracy_above_threshold(eval_results):
    """At least ACCURACY_THRESHOLD of cases are acceptable."""
    total = len(eval_results)
    acceptable = sum(
        1 for r in eval_results
        if r["output"] is not None and r["output"].category in r["case"]["acceptable"]
    )
    accuracy = acceptable / total
    _failures = [
        f"  - {r['case']['description']!r} → {r['output'].category if r['output'] else 'ERROR'} "
        f"(acceptable: {r['case']['acceptable']})"
        for r in eval_results
        if r["output"] is None or r["output"].category not in r["case"]["acceptable"]
    ]
    assert accuracy >= ACCURACY_THRESHOLD, (
        f"Accuracy {accuracy:.2%} below threshold {ACCURACY_THRESHOLD:.2%}.\n"
        f"Failing cases:\n" + "\n".join(_failures)
    )


def test_zero_catastrophic_failures(eval_results):
    """No case may be categorised as an explicitly unacceptable category."""
    catastrophics = [
        r for r in eval_results
        if r["output"] is not None and r["output"].category in r["case"]["unacceptable"]
    ]
    assert len(catastrophics) <= CATASTROPHIC_THRESHOLD, (
        f"{len(catastrophics)} catastrophic failure(s):\n"
        + "\n".join(
            f"  - {r['case']['description']!r} → {r['output'].category} "
            f"(explicitly unacceptable: {r['case']['unacceptable']})"
            for r in catastrophics
        )
    )


def test_p95_latency_below_ceiling(eval_results):
    """p95 per-request latency must be under the ceiling."""
    latencies = sorted(r["elapsed"] for r in eval_results)
    p95 = latencies[int(len(latencies) * 0.95)]
    assert p95 <= P95_LATENCY_SECONDS, (
        f"p95 latency {p95:.2f}s exceeds ceiling {P95_LATENCY_SECONDS}s. "
        f"mean={mean(latencies):.2f}s median={median(latencies):.2f}s max={max(latencies):.2f}s"
    )


def test_high_confidence_predictions_are_reliable(eval_results):
    """Rough calibration: when the model reports confidence ≥ 0.8, it should
    pick an acceptable category most of the time."""
    high_conf = [
        r for r in eval_results
        if r["output"] is not None and r["output"].confidence >= 0.8
    ]
    if not high_conf:
        pytest.skip("No high-confidence predictions in this run")

    acceptable = sum(
        1 for r in high_conf
        if r["output"].category in r["case"]["acceptable"]
    )
    rate = acceptable / len(high_conf)
    assert rate >= MIN_HIGH_CONF_ACCEPTABLE, (
        f"High-confidence acceptance rate {rate:.2%} below threshold "
        f"{MIN_HIGH_CONF_ACCEPTABLE:.2%}. The model is overconfident."
    )


# ---- a useful summary output (printed on any failure) -----------------------


def test_print_eval_summary(eval_results):
    """Not a real assertion — prints a summary after the other tests.

    Keep this as the last test alphabetically so pytest runs it last. The
    summary helps facilitators eyeball what the agent actually did.
    """
    total = len(eval_results)
    acceptable = sum(
        1 for r in eval_results
        if r["output"] is not None and r["output"].category in r["case"]["acceptable"]
    )
    catastrophics = sum(
        1 for r in eval_results
        if r["output"] is not None and r["output"].category in r["case"]["unacceptable"]
    )
    errors = sum(1 for r in eval_results if r["output"] is None)
    latencies = sorted(r["elapsed"] for r in eval_results)

    print("\n=== Eval summary ===")
    print(f"  total cases:       {total}")
    print(f"  acceptable:        {acceptable} ({acceptable / total:.1%})")
    print(f"  catastrophic:      {catastrophics}")
    print(f"  errors:            {errors}")
    print(f"  latency p50/p95:   {latencies[len(latencies) // 2]:.2f}s / {latencies[int(len(latencies) * 0.95)]:.2f}s")
    print()
    # Always passes — it's informational.
    assert True
