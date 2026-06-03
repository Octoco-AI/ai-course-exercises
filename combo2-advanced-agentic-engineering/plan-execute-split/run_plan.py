"""Partner B, step 1 — Pro plans.

Runs Gemini 2.5 Pro (premium tier, thinking ON) to produce a plan ONLY — no
implementation. Writes the plan to plan.md, which run_execute.py then executes.

    python run_plan.py

Edit task.md, not this file. Read the plan it produces before running the
executor — if it's hand-wavy or missing sections, tune PLANNER_PROMPT below and
run again. The planner prompt is where teams compound gains over time.
"""

from __future__ import annotations

import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

from pricing import Usage, report

load_dotenv()
MODEL = os.environ.get("PLANNER_MODEL", "gemini-2.5-pro")

PLANNER_PROMPT = """You are a senior engineering planner. Given this task:

{task}

Produce a plan with four sections:

## Task
[One-sentence restatement.]

## Decomposition
[Numbered list of independent sub-tasks. Each ~1-2 hours of mechanical work.
No more than 6 sub-tasks — if you need more, the task is too big.]

## Context per sub-task
[For each sub-task: which files to read, which patterns to follow, which tests
to run. Not reasoning — just the pointer list.]

## Validation
[For each sub-task: what 'done' looks like. Usually a test command or a
specific file-state assertion.]

Do not write any implementation code. The output is ONLY the plan.
"""


def main() -> int:
    if "GOOGLE_API_KEY" not in os.environ:
        print("ERROR: GOOGLE_API_KEY is not set. Copy .env.example to .env and add your key.")
        return 2

    task = open("task.md", encoding="utf-8").read()
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

    print(f"Planning with {MODEL} (thinking dynamic)...\n")
    t0 = time.perf_counter()
    response = client.models.generate_content(
        model=MODEL,
        contents=PLANNER_PROMPT.format(task=task),
        config=types.GenerateContentConfig(
            # -1 = dynamic: the model decides how much to think. Pro can't fully
            # disable thinking; thinking is billed as output, so watch the
            # "+N thinking" number in the report — that's most of the cost.
            thinking_config=types.ThinkingConfig(thinking_budget=-1),
        ),
    )
    elapsed = time.perf_counter() - t0

    plan = response.text
    print(plan)

    with open("plan.md", "w", encoding="utf-8") as f:
        f.write(plan)
    print("\n--- Plan written to plan.md ---")

    usage = Usage()
    usage.add(response.usage_metadata)
    report("Plan (Pro)", MODEL, usage, elapsed)
    print("\nReview plan.md, then run:  python run_execute.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
