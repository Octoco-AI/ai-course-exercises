"""The agent loop. Module 1 end state — blocking, three tools.

Thesis (per Thorsten Ball, ampcode.com):

    It's an LLM, a loop, and enough tokens.
"""

from __future__ import annotations

import anthropic

from .settings import Settings
from .tools import ToolSet


SYSTEM_PROMPT = """You are a codebase assistant. Use the available tools to
answer questions about the workspace. When you've finished answering, stop
calling tools."""


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

        # Tool calls in the response.
        tool_uses = [block for block in response.content if block.type == "tool_use"]
        if not tool_uses:
            # This shouldn't happen when stop_reason != "end_turn", but
            # guard anyway.
            return "ERROR: no tool calls but stop_reason != end_turn"

        # Dispatch each tool; batch all results into one user turn.
        tool_result_blocks = []
        for tool_use in tool_uses:
            result = tools.dispatch(tool_use.name, dict(tool_use.input))
            tool_result_blocks.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result,
            })

        messages.append({"role": "user", "content": tool_result_blocks})

    return "ERROR: agent did not finish within max turns"
