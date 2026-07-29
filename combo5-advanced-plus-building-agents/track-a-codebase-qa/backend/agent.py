"""The async agent loop.

Thesis (per Thorsten Ball, ampcode.com):

    It's an LLM, a loop, and enough tokens.

Module 11 builds this loop against Gemini (`google-genai`), async from the
start. Module 12 turns `run_agent` into `run_agent_streaming` — a `return`
becomes a stream of `yield`s — but the loop shape underneath (messages,
tool definitions, termination, dispatch) doesn't change.
"""

from __future__ import annotations

from google import genai
from google.genai import types

from .settings import Settings
from .tools import ToolSet


SYSTEM_PROMPT = """You are a codebase assistant. Use the available tools to
answer questions about the workspace. When you have finished answering, stop
calling tools."""


# -----------------------------------------------------------------------
# STEP 2 — the async loop skeleton (given)
# -----------------------------------------------------------------------
async def run_agent(user_message: str, *, tools: ToolSet, settings: Settings) -> str:
    """Returns the final agent response text."""
    client = genai.Client(api_key=settings.google_api_key)
    declarations = tools.schemas()
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[types.Tool(function_declarations=declarations)] if declarations else None,
        # Drive the tool loop ourselves — no SDK auto-calling.
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    contents = [types.Content(role="user", parts=[types.Part(text=user_message)])]

    for turn in range(settings.max_agent_turns):
        response = client.models.generate_content(
            model=settings.model, contents=contents, config=config
        )
        parts = response.candidates[0].content.parts or []

        # Append the model's turn to history VERBATIM — do NOT skip this
        # line, and do NOT rebuild the parts (see exercise.adoc's IMPORTANT
        # note: Gemini 3.x attaches a `thought_signature` to function-call
        # parts that rebuilding them would drop).
        contents.append(types.Content(role="model", parts=parts))

        function_calls = [p.function_call for p in parts if p.function_call]
        if not function_calls:
            return "".join(p.text for p in parts if p.text)

        # -----------------------------------------------------------------
        # STEP 4 — concurrent tool dispatch
        # -----------------------------------------------------------------
        # Hints:
        #   - Tools are synchronous; wrap each dispatch in
        #     `asyncio.to_thread(tools.dispatch, call.name, dict(call.args or {}))`
        #     so `asyncio.gather` is genuinely concurrent.
        #   - Wrap each result in `types.Part.from_function_response(name=call.name,
        #     response=payload)` — `payload` must be a dict, so wrap non-dict
        #     results as `{"result": result}`.
        #   - Append ALL responses in ONE `role="user"` Content — never one
        #     turn per result.
        #   - `import asyncio` at the top of this file.
        # TODO: Step 4 — dispatch tools concurrently, append one
        #       function-response turn, loop.
        raise NotImplementedError("Tool dispatch not yet implemented")

    return "ERROR: agent did not finish within max turns"
