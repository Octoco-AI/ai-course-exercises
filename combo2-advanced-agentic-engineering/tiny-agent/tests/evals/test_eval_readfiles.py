"""Evals for <feature>. Run with:
    pytest -m evals tests/evals/
"""

from __future__ import annotations
import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.evals

from starter.agent import run_agent


# The tiny agent's tools are rooted at the current working directory (the
# sandbox root is captured at import time), so we cannot point the agent at an
# external temp dir — `edit_file` would reject it as "outside the sandbox".
# Instead we run against the real sample_repo and reset the file between runs.
MATH_UTILS = Path("sample_repo/math_utils.py")


def _factorial_of_zero(path: Path) -> int:
    """Load the (possibly edited) module fresh and call factorial(0).

    Asserting on behaviour, not on the file's text: the deliberate bug is that
    factorial(0) returns 0; the repaired version returns 1.
    """
    spec = importlib.util.spec_from_file_location("_math_utils_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.factorial(0)


def test_agent_fixes_factorial_bug_4_of_5():
    original = MATH_UTILS.read_text()
    pass_count = 0
    failures = []
    try:
        for i in range(5):
            MATH_UTILS.write_text(original)  # reset to the buggy state each run
            run_agent(
                "Look through sample_repo/math_utils.py for a bug. "
                "If you find one, fix it with edit_file and explain what you changed."
            )
            if _factorial_of_zero(MATH_UTILS) == 1:
                pass_count += 1
            else:
                failures.append(f"Run {i+1}: factorial(0) still wrong")
    finally:
        MATH_UTILS.write_text(original)  # always restore the original file

    assert pass_count >= 4, (
            f"Agent fixed the bug only {pass_count}/5 times.\n"
            + "\n".join(failures)
    )