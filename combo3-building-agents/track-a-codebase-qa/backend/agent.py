"""The agent loop, streaming.

Same shape as Combo 1 M1's tiny-agent, but:
  - Anthropic instead of Gemini (Combo 3 reference provider)
  - Streaming — yields events as they happen instead of returning at the end
  - Four tools instead of three (adds search_docs)
  - Bounded by max_turns, explicit finish signal

Thesis (per Ball):

    It's an LLM, a loop, and enough tokens.

The streaming adds very little — it's still an LLM, a loop, and tokens that
flow to the client as they're generated rather than in one lump at the end.
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
from .tools import ToolSet, anthropic_tool_schemas


SYSTEM_PROMPT = """You are a codebase-Q&A assistant for the TodoMagic project. Your job:

1. Help users understand the codebase. They may ask about architecture,
   specific features, how things work, or how to do something.
2. Where useful, draft small changes via the `draft_patch` tool. Patches are
   reviewed by a human; you never modify the workspace directly.

Tools you have:
  - search_docs(query)          — find relevant passages in the docs/code.
  - read_file(path)             — read a file from the workspace.
  - list_files(path)            — list a workspace directory.
  - draft_patch(path, old, new) — propose a change as a unified-diff patch.

Workflow:
  1. If the question is vague, ask ONE clarifying question before searching.
  2. Use `search_docs` first for questions about behaviour, design, or
     "how does X work." Follow up with `read_file` for specific files.
  3. When citing, quote briefly (1-3 lines) and name the source file
     (and heading if available).
  4. For edit requests, draft a patch and ASK the user whether to apply it.
     Never assume approval; a drafted patch is a proposal, not an action.
  5. When you've answered the question, STOP calling tools. The next turn
     with no tool calls is your final answer.

Rules:
  - NEVER pretend to have done something you can't. You can't push to git,
    send email, run shell commands, or delete files. If the user asks for
    one of those, explain the limitation and offer a drafted patch if relevant.
  - Stay in the workspace. The search corpus and the workspace are your scope.
  - Cite sources. Anything you claim about the code should be findable.
"""


async def run_agent_streaming(
    user_message: str,
    *,
    history: list[dict] | None = None,
    settings: Settings,
    tools: ToolSet,
) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted strings as the agent runs.

    Args:
        user_message: The user's prompt.
        history: Optional prior conversation (list of {"role": ..., "content": ...}).
        settings: App config.
        tools: Bound tool set.

    Yields:
        SSE-framed strings. The caller writes them straight to the HTTP response.
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    tool_schemas = anthropic_tool_schemas()

    messages = list(history or [])
    messages.append({"role": "user", "content": user_message})

    final_text_parts: list[str] = []

    for turn in range(1, settings.max_agent_turns + 1):
        # Stream a single assistant turn. The SDK's .stream() context manager
        # yields text chunks as they arrive AND assembles the final Message
        # object we can use to detect tool calls.
        try:
            with client.messages.stream(
                model=settings.model,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                tools=tool_schemas,
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

        # Find any tool calls in this turn.
        tool_uses = [block for block in final_message.content if block.type == "tool_use"]

        if not tool_uses:
            # No tool calls → agent is done.
            yield done_event(turns=turn, final_text="".join(final_text_parts))
            return

        # Execute each tool call, one by one, and build a single tool_result
        # user-turn to send back next iteration.
        tool_result_blocks = []
        for tool_use in tool_uses:
            args_dict = dict(tool_use.input) if isinstance(tool_use.input, dict) else {}
            yield tool_call_event(name=tool_use.name, args=args_dict)

            result = _dispatch_tool(tools, tool_use.name, args_dict)
            preview = truncate_preview(result)
            yield tool_result_event(name=tool_use.name, result_preview=preview)

            # What the LLM sees: the raw result, serialised to a string.
            result_text = (
                result if isinstance(result, str) else json.dumps(result)
            )
            tool_result_blocks.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result_text,
            })

        messages.append({"role": "user", "content": tool_result_blocks})

    # Hit max_turns without finishing.
    yield error_event(f"Agent did not finish within {settings.max_agent_turns} turns.")


def _dispatch_tool(tools: ToolSet, name: str, args: dict) -> object:
    """Call the named tool method on `tools`. Returns whatever the tool returns.

    Tool errors are returned as strings starting with "ERROR:" so the LLM
    can self-correct — exceptions would break the stream.
    """
    method = getattr(tools, name, None)
    if method is None or not callable(method):
        return f"ERROR: unknown tool {name!r}"
    try:
        return method(**args)
    except TypeError as exc:
        return f"ERROR: bad arguments to {name}: {exc}"
    except Exception as exc:  # noqa: BLE001
        return f"ERROR: {type(exc).__name__}: {exc}"
