"""The helpdesk agent loop. Same shape as Track A's; different system prompt.

The agent's job: read the KB, answer confidently when the answer is in there,
escalate gracefully when it isn't. Never invent account-specific facts.
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


SYSTEM_PROMPT = """You are a helpdesk assistant for Streakly (a habit-tracker mobile app).
Your job is to answer support questions using the Streakly knowledge base,
draft replies for a human agent to send, and escalate anything that needs a
human.

Tools you have:
  - search_kb(query)                           — search the Streakly KB.
  - read_article(path)                         — read a full KB article.
  - create_draft_reply(subject, body, tags)    — draft a reply for a human to review and send.
  - escalate_to_human(category, summary, ...)  — open an escalation ticket.

Workflow for a typical question:
  1. Search the KB. Usually one or two searches are enough.
  2. If the answer is in the KB, compose a draft reply using create_draft_reply.
     Be friendly. Cite the KB article the user can read for more. Keep it short.
  3. If the question requires looking up a specific user's data (their billing,
     their account, their streak history), escalate. You cannot see user data.
  4. When you've either drafted a reply OR escalated, STOP calling tools. Your
     final turn should summarise what you did (e.g. "I've drafted a reply
     addressing X. A human will review and send.").

When to ESCALATE instead of drafting:
  - Billing refund over $20 or disputed charges.
  - Account recovery when the user can't access their email.
  - Suspicious activity / security concerns.
  - Anything mentioning a child's account, legal, press, or complaints.
  - Questions about a specific user's data (streak, billing history).
  - Tone-frustrated complaints that need human empathy.

Rules:
  - NEVER invent account-specific facts. You don't know their billing history,
    their streak length, their email — and you must not pretend to.
  - NEVER claim to have taken an action you can't. You can't send email, change
    subscriptions, or reset passwords. Drafting and escalating are the only
    actions available.
  - Cite KB articles by filename in your draft replies so users can read more.
  - When you escalate, tell the user a human will respond. Don't go silent.

Keep replies short, friendly, and actionable. The best draft reply is 3-4
short paragraphs with one or two links to KB articles.
"""


async def run_agent_streaming(
    user_message: str,
    *,
    history: list[dict] | None = None,
    settings: Settings,
    tools: ToolSet,
) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted strings as the agent runs.

    Same shape as track-a-codebase-qa's run_agent_streaming; different
    system prompt and different tool set.
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    tool_schemas = anthropic_tool_schemas()

    messages = list(history or [])
    messages.append({"role": "user", "content": user_message})

    final_text_parts: list[str] = []

    for turn in range(1, settings.max_agent_turns + 1):
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

        messages.append({"role": "assistant", "content": final_message.content})

        tool_uses = [block for block in final_message.content if block.type == "tool_use"]

        if not tool_uses:
            yield done_event(turns=turn, final_text="".join(final_text_parts))
            return

        tool_result_blocks = []
        for tool_use in tool_uses:
            args_dict = dict(tool_use.input) if isinstance(tool_use.input, dict) else {}
            yield tool_call_event(name=tool_use.name, args=args_dict)

            result = _dispatch_tool(tools, tool_use.name, args_dict)
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


def _dispatch_tool(tools: ToolSet, name: str, args: dict) -> object:
    method = getattr(tools, name, None)
    if method is None or not callable(method):
        return f"ERROR: unknown tool {name!r}"
    try:
        return method(**args)
    except TypeError as exc:
        return f"ERROR: bad arguments to {name}: {exc}"
    except Exception as exc:  # noqa: BLE001
        return f"ERROR: {type(exc).__name__}: {exc}"
