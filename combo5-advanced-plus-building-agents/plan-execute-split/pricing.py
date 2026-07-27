"""Token-usage accounting + cost reporting.

Keeps the dollar maths in one place so the run scripts stay short. Prices are
Gemini 3.x list prices (USD per 1M tokens) as used in the M7 exercise. Thinking
tokens are billed at the OUTPUT rate. Update the table if Google changes prices.

You should not need to edit this file to do the exercise — but the PRICES table
is the one thing worth checking against https://ai.google.dev/pricing if your
numbers look off.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# model id -> (input $/1M, output $/1M). Thinking billed at the output rate.
PRICES: dict[str, tuple[float, float]] = {
    "gemini-3.1-pro": (2.00, 12.0),        # premium / planner (Preview as of 2026-07)
    "gemini-3.5-flash": (1.50, 9.0),       # mid tier (GA)
    "gemini-3.1-flash-lite": (0.25, 1.50),  # budget / executor + monolithic (GA)
}

COMPARISON_FILE = Path("COMPARISON.md")


@dataclass
class Usage:
    """Running totals across one or more API calls."""

    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0
    turns: int = 0

    def add(self, usage_metadata) -> None:
        """Accumulate one response's usage_metadata into the running totals.

        Gemini's `generate_content` reports usage only for the call it returns.
        When the agent loops over several tool-calling turns we must add up
        every turn to get an accurate end-to-end total — that's why we track
        this ourselves instead of reading the final response alone.
        """
        if usage_metadata is None:
            return
        self.input_tokens += usage_metadata.prompt_token_count or 0
        self.output_tokens += usage_metadata.candidates_token_count or 0
        self.thinking_tokens += getattr(usage_metadata, "thoughts_token_count", 0) or 0
        self.turns += 1


def cost_usd(model: str, usage: Usage) -> float:
    """Dollar cost of `usage` at `model`'s list price. Thinking billed as output."""
    if model not in PRICES:
        print(f"  (no price on file for {model!r} — reporting $0; add it to PRICES)")
        return 0.0
    in_rate, out_rate = PRICES[model]
    return (
        usage.input_tokens * 1e-6 * in_rate
        + (usage.output_tokens + usage.thinking_tokens) * 1e-6 * out_rate
    )


def report(stage: str, model: str, usage: Usage, elapsed: float) -> float:
    """Print a tidy stage summary, append it to COMPARISON.md, return the cost."""
    cost = cost_usd(model, usage)
    print()
    print(f"  ── {stage} ──")
    print(f"  Model:         {model}")
    print(f"  Input tokens:  {usage.input_tokens}")
    print(f"  Output tokens: {usage.output_tokens} (+{usage.thinking_tokens} thinking)")
    print(f"  Approx cost:   ${cost:.4f}")
    print(f"  Wall-clock:    {elapsed:.1f}s")
    if usage.turns > 1:
        print(f"  (summed across {usage.turns} tool-calling turns)")

    block = [
        f"## {stage}",
        "",
        f"- Model: {model}",
        f"- Input tokens: {usage.input_tokens}",
        f"- Output tokens: {usage.output_tokens} (+{usage.thinking_tokens} thinking)",
        f"- Approx cost: ${cost:.4f}",
        f"- Wall-clock: {elapsed:.1f}s",
        "- Quality (fill in by hand):",
        "  - Tests pass? [yes/no]",
        "  - Spec met? [yes/partial/no — notes]",
        "  - Manual fixes needed? [what?]",
        "",
    ]
    with COMPARISON_FILE.open("a", encoding="utf-8") as f:
        f.write("\n".join(block) + "\n")
    print(f"  → appended to {COMPARISON_FILE}")
    return cost
