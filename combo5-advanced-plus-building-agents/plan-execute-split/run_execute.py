"""Partner B, step 2 — Flash executes.

Reads plan.md (produced by run_plan.py) and runs Gemini 3.1 Flash-Lite (budget tier,
thinking OFF) to implement it, with the same three file tools the monolithic run
used. Run run_plan.py first.

    python run_execute.py

Flash-Lite is already the budget tier. If it's too weak to follow the plan, set
EXECUTOR_MODEL=gemini-3.5-flash in .env for a stronger mid-tier executor — the
report prices all three tiers.
"""

from __future__ import annotations

import os
import time

from dotenv import load_dotenv

from agent import run_agent
from pricing import report
from tools import workspace_root

load_dotenv()
MODEL = os.environ.get("EXECUTOR_MODEL", "gemini-3.1-flash-lite")

EXECUTOR_PROMPT = """You are an implementation engineer. A senior engineer has
produced this plan. Execute each sub-task in order. For each:

1. Do the mechanical work (read files, write code via edit_file).
2. Report briefly what you did.
3. Move to the next sub-task.

Plan:
{plan}

Implement. Don't ask questions — make reasonable defaults. The plan is the
contract."""


def main() -> int:
    if "GOOGLE_API_KEY" not in os.environ:
        print("ERROR: GOOGLE_API_KEY is not set. Copy .env.example to .env and add your key.")
        return 2
    if not os.path.exists("plan.md"):
        print("ERROR: plan.md not found. Run `python run_plan.py` first.")
        return 2

    plan = open("plan.md", encoding="utf-8").read()
    print(f"Workspace: {workspace_root()}")
    print(f"Executing the plan with {MODEL} (thinking off)...\n")

    t0 = time.perf_counter()
    final_text, usage = run_agent(
        EXECUTOR_PROMPT.format(plan=plan), model=MODEL, thinking_budget=0
    )
    elapsed = time.perf_counter() - t0

    print("\n--- Agent finished ---")
    print(final_text)

    report("Execute (Flash)", MODEL, usage, elapsed)
    print("\nThe planner cost is the 'Plan (Pro)' section above it in COMPARISON.md.")
    print("Add the two for the split total, then compare against Flash monolithic.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
