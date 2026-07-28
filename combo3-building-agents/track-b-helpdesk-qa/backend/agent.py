"""The agent loop.

Thesis (per Thorsten Ball, ampcode.com):

    It's an LLM, a loop, and enough tokens.

Module 1 builds this loop against Anthropic, blocking (`-> str`). Module 3
turns `run_agent` into `run_agent_streaming` — a `return` becomes a stream
of `yield`s — but the loop shape underneath doesn't change.
"""

from __future__ import annotations

import anthropic

from .settings import Settings
from .tools import ToolSet


SYSTEM_PROMPT = """You are a helpdesk assistant for Streakly (a habit-tracker
mobile app). Use the available tools to triage tickets and draft replies.
When you've finished answering, stop calling tools."""


# -----------------------------------------------------------------------
# STEP 2 — the loop skeleton (given)
# -----------------------------------------------------------------------
def run_agent(
    user_message: str,
    *,
    tools: ToolSet,
    settings: Settings,
) -> str:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    messages = [{"role": "user", "content": user_message}]

    for turn in range(settings.max_agent_turns):
        response = client.messages.create(
            model=settings.model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=tools.schemas(),
            messages=messages,
        )

        # Append the assistant's turn to history — don't skip this.
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            return "".join(
                block.text for block in response.content if block.type == "text"
            )

        # -----------------------------------------------------------------
        # STEP 4 — tool dispatch
        # -----------------------------------------------------------------
        # Hints:
        #   - Tool calls are the `tool_use` blocks in `response.content`.
        #   - Dispatch each via `tools.dispatch(tool_use.name, dict(tool_use.input))`.
        #   - Build ONE user turn with all `tool_result` blocks:
        #     `{"type": "tool_result", "tool_use_id": tool_use.id, "content": result}`.
        #   - `tool_use_id` must be `tool_use.id` (not `.name`).
        # TODO: Step 4 — dispatch tools, append the tool_result turn, continue the loop.
        raise NotImplementedError("Tool dispatch not yet implemented")

    return "ERROR: agent did not finish within max turns"
