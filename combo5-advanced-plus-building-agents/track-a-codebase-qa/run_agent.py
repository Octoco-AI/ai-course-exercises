#!/usr/bin/env python3
"""CLI entry point for the agent. Given — no changes needed.

Module 11 ships a blocking `run_agent(...) -> str`; this prints the final
answer. Module 12 renames it to `run_agent_streaming(...)` (an async
generator) — pass `--stream` to drive that instead and print raw SSE
events as they arrive. That's the fastest way to see streaming work
without spinning up the FastAPI server + UI (see exercise.adoc Step A.4).

Usage:
    python run_agent.py "What files exist in the workspace?"
    python run_agent.py --stream "What files exist in the workspace?"
"""

from __future__ import annotations

import asyncio
import sys

from dotenv import load_dotenv

from backend.settings import load_settings
from backend.tools import build_toolset


def main() -> int:
    raw_args = sys.argv[1:]
    stream = "--stream" in raw_args
    args = [a for a in raw_args if a != "--stream"]
    if not args:
        print('Usage: python run_agent.py ["--stream"] "<your prompt>"', file=sys.stderr)
        return 1
    prompt = " ".join(args)

    load_dotenv()
    try:
        settings = load_settings()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    tools = build_toolset(settings.workspace_root)

    import backend.agent as agent_module

    if stream:
        run_agent_streaming = getattr(agent_module, "run_agent_streaming", None)
        if run_agent_streaming is None:
            print(
                "ERROR: run_agent_streaming isn't implemented yet — that's Module 12.",
                file=sys.stderr,
            )
            return 2

        async def _run_stream() -> None:
            async for event in run_agent_streaming(prompt, settings=settings, tools=tools):
                print(event, end="", flush=True)

        asyncio.run(_run_stream())
        return 0

    run_agent = getattr(agent_module, "run_agent", None)
    if run_agent is None:
        print(
            "ERROR: run_agent isn't defined — did Module 12 already rename it to "
            "run_agent_streaming? Pass --stream.",
            file=sys.stderr,
        )
        return 2

    result = asyncio.run(run_agent(prompt, tools=tools, settings=settings))
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
