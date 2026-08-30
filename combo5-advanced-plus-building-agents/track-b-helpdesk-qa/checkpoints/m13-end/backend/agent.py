"""The agent loop — streaming. Module 12 end state.

`run_agent` (Module 11's blocking `-> str` loop) is now `run_agent_streaming`
(an `AsyncGenerator[str, None]`): the single `return` became `yield`s as
events happen, and `generate_content(...)` became
`generate_content_stream(...)`. Termination, dispatch, and the verbatim
model-turn append (thought_signature) are unchanged from Module 11.

Note: this streaming version dispatches tool calls sequentially (not via
`asyncio.gather` as Module 11's did) — that's what lets each tool_call /
tool_result pair get its own event, in order, as it happens.
"""

from __future__ import annotations

from typing import AsyncGenerator

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
from .tools import ToolSet


SYSTEM_PROMPT = """You are a helpdesk assistant for Streakly (a habit-tracker
mobile app). Use the available tools to triage tickets and draft replies.
When you have finished answering, stop calling tools."""


async def run_agent_streaming(
    user_message: str,
    *,
    settings: Settings,
    tools: ToolSet,
    history: list[dict] | None = None,
) -> AsyncGenerator[str, None]:
    client = genai.Client(api_key=settings.google_api_key)
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[types.Tool(function_declarations=tools.schemas())],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    contents = _history_to_gemini(history)
    contents.append(types.Content(role="user", parts=[types.Part(text=user_message)]))

    final_text_parts: list[str] = []

    for turn in range(settings.max_agent_turns):
        function_calls = []
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
                    # Keep the ORIGINAL part object — Gemini 3.x function-call
                    # parts carry a thought_signature that must be echoed back.
                    turn_parts.append(part)
                    if getattr(part, "text", None):
                        final_text_parts.append(part.text)
                        yield text_event(part.text)
                    elif getattr(part, "function_call", None):
                        function_calls.append(part.function_call)
        except Exception as exc:  # noqa: BLE001 — surface any API error to the client
            yield error_event(f"Gemini API error: {exc}")
            return

        # Persist the model turn VERBATIM (preserves thought_signature).
        contents.append(
            types.Content(role="model", parts=turn_parts or [types.Part(text="")])
        )

        if not function_calls:
            yield done_event(turns=turn + 1, final_text="".join(final_text_parts))
            return

        response_parts: list[types.Part] = []
        for call in function_calls:
            args = dict(call.args or {})
            yield tool_call_event(name=call.name, args=args)

            result = tools.dispatch(call.name, args)
            yield tool_result_event(
                name=call.name,
                result_preview=truncate_preview(result),
            )

            payload = result if isinstance(result, dict) else {"result": result}
            response_parts.append(
                types.Part.from_function_response(name=call.name, response=payload)
            )

        contents.append(types.Content(role="user", parts=response_parts))

    yield error_event(f"Agent did not finish within {settings.max_agent_turns} turns")


def _history_to_gemini(history: list[dict] | None) -> list[types.Content]:
    """Convert the UI's provider-neutral {role, content} history into Content objects."""
    out: list[types.Content] = []
    for item in history or []:
        role = "model" if item.get("role") in ("assistant", "model") else "user"
        out.append(types.Content(role=role, parts=[types.Part(text=item.get("content", ""))]))
    return out
