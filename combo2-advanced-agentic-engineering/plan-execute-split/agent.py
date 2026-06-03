"""The agent loop, shared by the monolithic and executor runs.

This is the Combo 1 / M1 tiny-agent loop with one addition: it accumulates
`usage_metadata` across EVERY tool-calling turn, so the cost numbers the run
scripts print are accurate end-to-end totals — not just the final turn. (A
single `generate_content` call reports usage only for that call; the SDK's
automatic function calling hides the intermediate turns. We run the loop
ourselves so we can see and sum them.)

You should not need to edit this file to do the exercise.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from pricing import Usage
from tools import TOOLS, edit_file, list_files, read_file

# Map the tool name (as the model sees it) to the actual Python callable.
TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_files": list_files,
    "edit_file": edit_file,
}


def run_agent(
    prompt: str,
    *,
    model: str,
    thinking_budget: int = 0,
    max_turns: int = 30,
) -> tuple[str, Usage]:
    """Run the loop until the model stops calling tools.

    Args:
        prompt: The full instruction (task, or executor prompt with the plan).
        model: Gemini model id, e.g. "gemini-2.5-flash".
        thinking_budget: 0 disables thinking (Flash/Flash-Lite only); -1 lets
            the model think dynamically; a positive int is a hard ceiling.
        max_turns: Hard cap on loop iterations to prevent runaway spend.

    Returns:
        (final_text, usage) — usage is summed across all turns.
    """
    load_dotenv()
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

    contents: list[types.Content] = [
        types.Content(role="user", parts=[types.Part(text=prompt)])
    ]

    config = types.GenerateContentConfig(
        tools=TOOLS,
        thinking_config=types.ThinkingConfig(thinking_budget=thinking_budget),
        # Disable the SDK's automatic function calling so we drive the loop and
        # can sum usage across turns ourselves.
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    usage = Usage()

    for turn in range(1, max_turns + 1):
        response = client.models.generate_content(
            model=model, contents=contents, config=config
        )
        usage.add(response.usage_metadata)

        candidate = response.candidates[0]
        contents.append(candidate.content)

        function_calls = [
            part.function_call
            for part in candidate.content.parts or []
            if part.function_call
        ]

        if not function_calls:
            final_text = "".join(
                part.text or "" for part in candidate.content.parts or []
            )
            return final_text, usage

        response_parts: list[types.Part] = []
        for call in function_calls:
            name = call.name
            args = {k: v for k, v in (call.args or {}).items()}
            args_preview = ", ".join(f"{k}={v!r}" for k, v in args.items())
            if len(args_preview) > 100:
                args_preview = args_preview[:97] + "..."
            print(f"  → {name}({args_preview})")

            fn = TOOL_FUNCTIONS.get(name)
            if fn is None:
                result = f"ERROR: unknown tool {name!r}"
            else:
                try:
                    result = fn(**args)
                except TypeError as exc:
                    result = f"ERROR: bad arguments to {name}: {exc}"
                except Exception as exc:  # noqa: BLE001 — surface tool failures to the model
                    result = f"ERROR: {type(exc).__name__}: {exc}"

            preview = result if isinstance(result, str) else f"[{len(result)} items]"
            if isinstance(preview, str) and len(preview) > 120:
                preview = preview[:117] + "..."
            print(f"    {preview}")

            response_parts.append(
                types.Part.from_function_response(name=name, response={"result": result})
            )

        contents.append(types.Content(role="user", parts=response_parts))

    return f"ERROR: agent did not finish within {max_turns} turns", usage
