"""The agent loop, streaming.

Same shape as Combo 1 M1's tiny-agent, but:
  - Streaming — yields events as they happen instead of returning at the end
  - Four tools instead of three (adds search_docs)
  - Bounded by max_turns, explicit finish signal

Two providers, same loop. **Gemini is the default** (the key Octoco provides);
Anthropic is the alternative for anyone who brings a Claude key. Which one runs
is decided by `settings.provider` (see `settings.py`). The two implementations
are deliberately parallel so you can read them side by side and see that "an
LLM, a loop, and enough tokens" is provider-agnostic.

Thesis (per Ball):

    It's an LLM, a loop, and enough tokens.

The streaming adds very little — it's still an LLM, a loop, and tokens that
flow to the client as they're generated rather than in one lump at the end.
"""

from __future__ import annotations

import json
from typing import AsyncGenerator

import anthropic
from google import genai
from google.genai import types

from .settings import Settings
from .streaming import (
    done_event,
    error_event,
    text_event,
    tool_call_event,
    tool_result_event,
    truncate_preview,
)
from .tools import ToolSet, anthropic_tool_schemas, gemini_tool_schemas


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

    Dispatches to the Gemini or Anthropic implementation based on
    `settings.provider`. Both yield the same event shapes (see `streaming.py`),
    so the server and UI don't care which provider is in use.
    """
    impl = _run_anthropic_streaming if settings.provider == "anthropic" else _run_gemini_streaming
    async for event in impl(user_message, history=history, settings=settings, tools=tools):
        yield event


# ---------------------------------------------------------------------------
# Gemini — the default provider (google-genai SDK).
# ---------------------------------------------------------------------------


async def _run_gemini_streaming(
    user_message: str,
    *,
    history: list[dict] | None,
    settings: Settings,
    tools: ToolSet,
) -> AsyncGenerator[str, None]:
    client = genai.Client(api_key=settings.google_api_key)
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[types.Tool(function_declarations=gemini_tool_schemas())],
        # We drive the tool loop ourselves so we can stream tool events to the
        # UI. Otherwise the SDK would run tools internally and hide the loop.
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    # Gemini's "contents" is an ordered list of Content objects. Function
    # responses go back as a user turn whose parts are function_response parts.
    contents = _history_to_gemini(history)
    contents.append(types.Content(role="user", parts=[types.Part(text=user_message)]))

    final_text_parts: list[str] = []

    for turn in range(1, settings.max_agent_turns + 1):
        turn_text = ""
        function_calls: list = []
        turn_parts: list[types.Part] = []
        try:
            stream = client.models.generate_content_stream(
                model=settings.model, contents=contents, config=config
            )
            for chunk in stream:
                candidate = chunk.candidates[0] if chunk.candidates else None
                if not (candidate and candidate.content and candidate.content.parts):
                    continue
                for part in candidate.content.parts:
                    # Read parts directly rather than chunk.text — the .text
                    # accessor warns/raises when a chunk mixes text + calls.
                    has_text = bool(getattr(part, "text", None))
                    has_call = bool(getattr(part, "function_call", None))
                    if not (has_text or has_call):
                        continue
                    # Keep the ORIGINAL part object. Gemini 3.x attaches a
                    # `thought_signature` to function-call parts that MUST be
                    # echoed back on the next turn — rebuilding the part drops
                    # it and the API rejects the follow-up with a 400.
                    turn_parts.append(part)
                    if has_text:
                        turn_text += part.text
                        yield text_event(part.text)
                    elif has_call:
                        function_calls.append(part.function_call)
        except Exception as exc:  # noqa: BLE001 — surface any API error to the client
            yield error_event(f"Gemini API error: {exc}")
            return

        final_text_parts.append(turn_text)

        # Persist this turn's model content verbatim (preserving thought
        # signatures) so the next request has the full, valid history.
        contents.append(
            types.Content(role="model", parts=turn_parts or [types.Part(text="")])
        )

        if not function_calls:
            yield done_event(turns=turn, final_text="".join(final_text_parts))
            return

        # Execute each tool call; send all results back in one user turn.
        response_parts: list[types.Part] = []
        for call in function_calls:
            name = call.name
            args = {k: v for k, v in (call.args or {}).items()}
            yield tool_call_event(name=name, args=args)

            result = _dispatch_tool(tools, name, args)
            yield tool_result_event(name=name, result_preview=truncate_preview(result))

            # from_function_response requires a dict; wrap str/list results.
            payload = result if isinstance(result, dict) else {"result": result}
            response_parts.append(
                types.Part.from_function_response(name=name, response=payload)
            )
        contents.append(types.Content(role="user", parts=response_parts))

    yield error_event(f"Agent did not finish within {settings.max_agent_turns} turns.")


def _history_to_gemini(history: list[dict] | None) -> list[types.Content]:
    """Convert the UI's provider-neutral history into Gemini Content objects."""
    out: list[types.Content] = []
    for item in history or []:
        role = "model" if item.get("role") in ("assistant", "model") else "user"
        content = item.get("content", "")
        if isinstance(content, str):
            text = content
        else:
            # A list of content blocks — pull out any text.
            text = " ".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            )
        out.append(types.Content(role=role, parts=[types.Part(text=text)]))
    return out


# ---------------------------------------------------------------------------
# Anthropic — the alternative provider (anthropic SDK).
# ---------------------------------------------------------------------------


async def _run_anthropic_streaming(
    user_message: str,
    *,
    history: list[dict] | None,
    settings: Settings,
    tools: ToolSet,
) -> AsyncGenerator[str, None]:
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
