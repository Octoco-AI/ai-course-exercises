"""The agent loop. This is the file attendees write in Combo 1 M1.

Thesis (Thorsten Ball, ampcode.com):

    It's an LLM, a loop, and enough tokens.

That's it. No framework magic. Roughly 100 lines of Python wraps the
Gemini API into a working coding agent.

Usage:

    python -m reference.agent "List the files here and describe what this code does"

What the loop does, in one glance:

    messages = [user_prompt]
    while True:
        response = gemini.generate(messages, tools=[read_file, list_files, edit_file])
        messages.append(response)
        if response has no tool calls:
            return response.text
        for each tool call in response:
            result = run the tool
            messages.append(tool_result)
        # go round again
"""

from __future__ import annotations

import os
import sys

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


# Map the tool name (as the model sees it) to the actual Python callable.
# The Gemini SDK auto-generates the name from the function name, so these match.
TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_files": list_files,
    "edit_file": edit_file,
}


def run_agent(
    user_prompt: str,
    *,
    model: str | None = None,
    max_turns: int = 20,
    on_event=None,
) -> str:
    """Run the agent loop until the model returns a final answer.

    Args:
        user_prompt: The initial user question or task.
        model: Gemini model id. Defaults to env var GEMINI_MODEL or gemini-3.1-flash-lite.
        max_turns: Hard cap on loop iterations to prevent runaway spend.
        on_event: Optional callback invoked for each loop event. Gets a dict with
            keys like {"type": "tool_call", "name": ..., "args": ...} — useful for
            streaming activity to a UI or a log. In the CLI we just print.

    Returns:
        The model's final text. If max_turns is hit, returns an error string.
    """
    load_dotenv()
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    model = model or os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")

    def emit(event):
        if on_event is not None:
            on_event(event)

    # ---- conversation state --------------------------------------------------
    # Gemini's "contents" is an ordered list of Content objects alternating
    # between roles "user" and "model". Function responses go back as a user
    # turn whose parts are function_response parts.
    contents: list[types.Content] = [
        types.Content(role="user", parts=[types.Part(text=user_prompt)])
    ]

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=TOOLS,
        # We want to SEE the loop. The SDK would otherwise run tools itself and
        # only return the final text — great for production, bad for learning.
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    # ---- the loop ------------------------------------------------------------
    for turn in range(1, max_turns + 1):
        emit({"type": "turn_start", "turn": turn})

        response = client.models.generate_content(
            model=model, contents=contents, config=config
        )

        # The model's turn always has exactly one candidate for our use case.
        candidate = response.candidates[0]
        contents.append(candidate.content)

        # Collect function calls (if any) from this response.
        function_calls = [
            part.function_call
            for part in candidate.content.parts or []
            if part.function_call
        ]

        if not function_calls:
            # No tool calls → the model signalled it's done.
            final_text = "".join(part.text or "" for part in candidate.content.parts or [])
            emit({"type": "final", "text": final_text, "turns": turn})
            return final_text

        # Execute each tool call and collect the responses.
        response_parts: list[types.Part] = []
        for call in function_calls:
            name = call.name
            # call.args is a proto-backed mapping; convert to a plain dict.
            args = {k: v for k, v in (call.args or {}).items()}
            emit({"type": "tool_call", "name": name, "args": args})

            fn = TOOL_FUNCTIONS.get(name)
            if fn is None:
                result = f"ERROR: unknown tool {name!r}"
            else:
                try:
                    result = fn(**args)
                except TypeError as exc:
                    # Mis-shaped arguments — e.g. missing required param.
                    result = f"ERROR: bad arguments to {name}: {exc}"
                except Exception as exc:  # noqa: BLE001 — surface any tool failure to the LLM
                    result = f"ERROR: {type(exc).__name__}: {exc}"

            emit({"type": "tool_result", "name": name, "result": result})
            response_parts.append(
                types.Part.from_function_response(
                    name=name,
                    # The SDK requires a dict here. Wrap str / list results.
                    response={"result": result},
                )
            )

        # Send all tool responses back in a single user turn.
        contents.append(types.Content(role="user", parts=response_parts))

    return f"ERROR: agent did not finish within {max_turns} turns"


# ---- CLI entrypoint ----------------------------------------------------------


def _print_event(event: dict) -> None:
    """Default event printer — one line per meaningful action."""
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
        print('Usage: python -m reference.agent "<your prompt>"', file=sys.stderr)
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
