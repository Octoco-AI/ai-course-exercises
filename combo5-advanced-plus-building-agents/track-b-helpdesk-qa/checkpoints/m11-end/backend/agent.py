"""The async agent loop. Module 11 end state — concurrent tool dispatch.

Thesis (per Thorsten Ball, ampcode.com):

    It's an LLM, a loop, and enough tokens.
"""

from __future__ import annotations

import asyncio

from google import genai
from google.genai import types

from .settings import Settings
from .tools import ToolSet


SYSTEM_PROMPT = """You are a helpdesk assistant for Streakly (a habit-tracker
mobile app). Use the available tools to triage tickets and draft replies.
When you have finished answering, stop calling tools."""


async def _dispatch_one(tools: ToolSet, call) -> types.Part:
    result = await asyncio.to_thread(tools.dispatch, call.name, dict(call.args or {}))
    payload = result if isinstance(result, dict) else {"result": result}
    return types.Part.from_function_response(name=call.name, response=payload)


async def run_agent(user_message: str, *, tools: ToolSet, settings: Settings) -> str:
    """Returns the final agent response text."""
    client = genai.Client(api_key=settings.google_api_key)
    declarations = tools.schemas()
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[types.Tool(function_declarations=declarations)] if declarations else None,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    contents = [types.Content(role="user", parts=[types.Part(text=user_message)])]

    for turn in range(settings.max_agent_turns):
        response = client.models.generate_content(
            model=settings.model, contents=contents, config=config
        )
        parts = response.candidates[0].content.parts or []
        contents.append(types.Content(role="model", parts=parts))

        function_calls = [p.function_call for p in parts if p.function_call]
        if not function_calls:
            return "".join(p.text for p in parts if p.text)

        response_parts = await asyncio.gather(
            *[_dispatch_one(tools, call) for call in function_calls]
        )
        contents.append(types.Content(role="user", parts=list(response_parts)))

    return "ERROR: agent did not finish within max turns"
