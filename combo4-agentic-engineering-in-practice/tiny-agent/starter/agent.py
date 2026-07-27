"""The agent loop. Your job in step 1 is to make this loop work.

Thesis (Thorsten Ball, ampcode.com):

    It's an LLM, a loop, and enough tokens.

The shape of the loop you're going to write:

    contents = [user_prompt]
    while turn < max_turns:
        response = gemini.generate(contents, tools=TOOLS)
        contents.append(response.content)
        function_calls = [ ... extract from response ... ]
        if not function_calls:
            return response.text   # done
        for each call in function_calls:
            result = TOOL_FUNCTIONS[call.name](**call.args)
            append a function_response Part to contents
        # go round again
"""

from __future__ import annotations

import os
import sys
from typing import Any, Callable, cast

from dotenv import load_dotenv
from google import genai
from google.genai import types

from .tools import TOOLS, edit_file, list_files, read_file


SYSTEM_INSTRUCTION = """You are a careful coding assistant working inside a small
code repository. You have three tools: read_file, list_files, and edit_file.

Workflow:
1. Explore first. Use list_files and read_file to build an understanding before editing.
2. Edit sparingly. One edit per logical change. Use enough surrounding context in
   old_str so it matches exactly once.
3. Report what you did in plain prose when you are finished. Do not call any tool on
   the final turn — that's how you signal you're done.
4. If a tool returns a string starting with "ERROR:", read the error carefully and
   adjust your approach. Don't retry the same call blindly.
"""


TOOL_FUNCTIONS: dict[str, Callable[..., object]] = {
    "read_file": read_file,
    "list_files": list_files,
    "edit_file": edit_file,
}


# -----------------------------------------------------------------------------
# STEP 1 — implement run_agent
# -----------------------------------------------------------------------------
def run_agent(
    user_prompt: str,
    *,
    model: str | None = None,
    max_turns: int = 20,
    on_event=None,
) -> str:
    """Run the agent loop until the model returns a final answer.

    Hints:
      - `client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])`
      - `contents = [types.Content(role="user", parts=[types.Part(text=user_prompt)])]`
      - `config = types.GenerateContentConfig(system_instruction=..., tools=TOOLS,
             automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))`
      - `response = client.models.generate_content(model=model, contents=contents, config=config)`
      - Function calls are in `response.candidates[0].content.parts[i].function_call`.
      - To send a result back, append `types.Content(role="user", parts=[Part.from_function_response(name=..., response={"result": ...})])`.
      - Termination: the candidate has no `.function_call` parts.
    """
    load_dotenv()
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    model = model or os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

    def emit(event):
        if on_event is not None:
            on_event(event)

    # Gemini's "contents" is an ordered list of Content objects. The user's
    # prompt starts it; function responses are appended back as user turns.
    contents: list[types.Content] = [
        types.Content(role="user", parts=[types.Part(text=user_prompt)])
    ]

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        # cast: the SDK types `tools` as an invariant list, so a plain
        # list[Callable] doesn't satisfy it even though callables are accepted.
        tools=cast("list[Any]", TOOLS),
        # We drive the tool loop ourselves so we can SEE each step. Otherwise
        # the SDK runs the tools and only hands back the final text.
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    for turn in range(1, max_turns + 1):
        emit({"type": "turn_start", "turn": turn})

        response = client.models.generate_content(
            model=model, contents=contents, config=config
        )

        # The SDK types these as optional; guard so the rest of the loop works
        # with concrete objects (and mypy stays happy).
        if not response.candidates:
            return "ERROR: model returned no candidates"
        content = response.candidates[0].content
        if content is None:
            return "ERROR: model returned an empty response"
        contents.append(content)

        function_calls = [
            part.function_call
            for part in content.parts or []
            if part.function_call
        ]

        if not function_calls:
            # No tool calls → the model signalled it's done.
            final_text = "".join(part.text or "" for part in content.parts or [])
            emit({"type": "final", "text": final_text, "turns": turn})
            return final_text

        response_parts: list[types.Part] = []
        for call in function_calls:
            name = call.name or "<unknown>"
            args = dict(call.args or {})
            emit({"type": "tool_call", "name": name, "args": args})

            fn = TOOL_FUNCTIONS.get(name)
            result: object
            if fn is None:
                result = f"ERROR: unknown tool {name!r}"
            else:
                try:
                    result = fn(**args)
                except TypeError as exc:
                    result = f"ERROR: bad arguments to {name}: {exc}"
                except Exception as exc:  # noqa: BLE001 — surface any tool failure to the LLM
                    result = f"ERROR: {type(exc).__name__}: {exc}"

            emit({"type": "tool_result", "name": name, "result": result})
            response_parts.append(
                types.Part.from_function_response(
                    name=name,
                    response={"result": result},
                )
            )

        # Send all tool responses back in a single user turn, then loop.
        contents.append(types.Content(role="user", parts=response_parts))

    return f"ERROR: agent did not finish within {max_turns} turns"


# ---- CLI entrypoint (given — no changes needed) ------------------------------


def _print_event(event: dict) -> None:
    """Default event printer. Called from run_agent via on_event."""
    kind = event.get("type")
    if kind == "tool_call":
        args_preview = ", ".join(f"{k}={v!r}" for k, v in event["args"].items())
        if len(args_preview) > 120:
            args_preview = args_preview[:117] + "..."
        print(f"  → {event['name']}({args_preview})")
    elif kind == "tool_result":
        result = event["result"]
        if isinstance(result, list):
            result = f"[{len(result)} items]"
        elif isinstance(result, str) and len(result) > 200:
            result = result[:197] + "..."
        print(f"    {result}")


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: python -m starter.agent "<your prompt>"', file=sys.stderr)
        return 1
    prompt = " ".join(sys.argv[1:])
    try:
        final = run_agent(prompt, on_event=_print_event)
    except KeyError as exc:
        if str(exc) == "'GOOGLE_API_KEY'":
            print("ERROR: GOOGLE_API_KEY is not set. Copy .env.example to .env.", file=sys.stderr)
            return 2
        raise
    print()
    print(final)
    return 0


if __name__ == "__main__":
    sys.exit(main())
