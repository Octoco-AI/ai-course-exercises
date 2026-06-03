"""Partner A — Flash monolithic.

Runs the whole task in one agent loop with Gemini 2.5 Flash (budget tier,
thinking OFF). This is the baseline the plan/execute split is measured against.

    python run_monolithic.py

Edit task.md, not this file. Set WORKSPACE in .env to the repo you want the
agent to work on (default: the expense-categoriser exercise).
"""

from __future__ import annotations

import os
import time

from dotenv import load_dotenv

from agent import run_agent
from pricing import report
from tools import workspace_root

load_dotenv()
MODEL = os.environ.get("MONOLITHIC_MODEL", "gemini-2.5-flash")


def main() -> int:
    if "GOOGLE_API_KEY" not in os.environ:
        print("ERROR: GOOGLE_API_KEY is not set. Copy .env.example to .env and add your key.")
        return 2

    task = open("task.md", encoding="utf-8").read()
    print(f"Workspace: {workspace_root()}")
    print(f"Running {MODEL} monolithic on the task in task.md...\n")

    t0 = time.perf_counter()
    final_text, usage = run_agent(task, model=MODEL, thinking_budget=0)
    elapsed = time.perf_counter() - t0

    print("\n--- Agent finished ---")
    print(final_text)

    report("Flash monolithic", MODEL, usage, elapsed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
