"""The agent loop — streaming. Module 3 end state.

`run_agent` (Module 1's blocking `-> str` loop) is now `run_agent_streaming`
(an `AsyncGenerator[str, None]`): the single `return` became `yield`s as
events happen. The Anthropic client itself is still the *synchronous*
client — `client.messages.stream()` is a blocking context manager; wrapping
the outer function as `async def ... yield` is what lets FastAPI's
`StreamingResponse` consume it, not true non-blocking I/O. (The stretch in
Module 1 — `AsyncAnthropic` + `asyncio.gather` — is the fully-async version;
this module doesn't require it.)
"""

from __future__ import annotations

import json
from typing import AsyncGenerator

import anthropic

from .settings import Settings
from .streaming import (
    done_event,
    error_event,
    text_event,
    tool_call_event,
    tool_result_event,
    truncate_preview,
)
from .tools import ToolSet


SYSTEM_PROMPT = """You are a codebase assistant. Use the available tools to
answer questions about the workspace. When you've finished answering, stop
calling tools."""


async def run_agent_streaming(
    user_message: str,
    *,
    settings: Settings,
    tools: ToolSet,
    history: list[dict] | None = None,
) -> AsyncGenerator[str, None]:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    messages = list(history or [])
    messages.append({"role": "user", "content": user_message})

    final_text_parts: list[str] = []

    for turn in range(1, settings.max_agent_turns + 1):
        try:
            with client.messages.stream(
                model=settings.model,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                tools=tools.schemas(),
                messages=messages,
            ) as stream:
                for text_chunk in stream.text_stream:
                    if text_chunk:
                        final_text_parts.append(text_chunk)
                        yield text_event(text_chunk)
                final_message = stream.get_final_message()
        except anthropic.APIError as exc:
            yield error_event(f"Anthropic API error: {exc}")
            return

        # Persist the assistant's turn in the running history.
        messages.append({"role": "assistant", "content": final_message.content})

        tool_uses = [block for block in final_message.content if block.type == "tool_use"]

        if not tool_uses:
            yield done_event(turns=turn, final_text="".join(final_text_parts))
            return

        tool_result_blocks = []
        for tool_use in tool_uses:
            args_dict = dict(tool_use.input) if isinstance(tool_use.input, dict) else {}
            yield tool_call_event(name=tool_use.name, args=args_dict)

            result = tools.dispatch(tool_use.name, args_dict)
            preview = truncate_preview(result)
            yield tool_result_event(name=tool_use.name, result_preview=preview)

            result_text = result if isinstance(result, str) else json.dumps(result)
            tool_result_blocks.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result_text,
            })

        messages.append({"role": "user", "content": tool_result_blocks})

    yield error_event(f"Agent did not finish within {settings.max_agent_turns} turns.")
