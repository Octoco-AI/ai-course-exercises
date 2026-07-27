# Design Review — Tiny Agent `run_agent` + tools

- **Date:** 2026-07-22
- **Reviewer:** Staff engineer (design review)
- **Branch:** `exercise/flexi`
- **Scope reviewed:** local uncommitted changes (highest-priority target)
  - `starter/agent.py` — `run_agent` implemented; typing imports + `TOOL_FUNCTIONS` annotation added
  - `starter/tools.py` — `read_file`, `list_files`, `edit_file` implemented
  - `verify.sh` — default model id bumped
- **Reference for comparison:** `reference/agent.py`, `reference/tools.py` (the repo's own worked solution / canonical pattern)

This is a design review only. Style, naming, and test coverage were deliberately out of scope.

---

## Most consequential design decision

**Hand-rolling the agent loop with `automatic_function_calling` disabled and dispatching tools manually through the `TOOL_FUNCTIONS` name→callable map** (`starter/agent.py:99`, `:136`).

**Verdict: right.**

The entire point of the exercise — and the CLI's `on_event` contract (`tool_call` / `tool_result` / `turn_start` / `final` events consumed by `_print_event`) — depends on the loop being visible. If the SDK's automatic function calling were left on, it would execute tools internally and hand back only final text, collapsing every per-step event and making the `on_event` callback dead code. The manual loop is the correct abstraction for the stated goal (observability / learning), and it matches the reference implementation exactly.

The alternative (enable automatic function calling, delete the dispatch loop) would be shorter but would break the event stream and the CLI's step-by-step output — the wrong trade for this codebase.

---

## Design fidelity

The change faithfully reproduces the established pattern in this repo rather than inventing a second way of doing things:

- **Tools (`starter/tools.py`) are effectively identical to `reference/tools.py`** — same `_resolve` reuse, same exists/is_file/is_dir guards, same errors-as-strings convention, same exact-match-once rule in `edit_file`. No parallel abstraction, no logic duplicated that should have been extracted.
- **Layering is correct.** Filesystem logic stays in `tools.py`; the loop and tool dispatch stay in `run_agent`; presentation stays in `_print_event`/`main`. No business logic leaking into the CLI layer and no I/O leaking into the loop.
- **Error convention preserved.** New failure paths return `"ERROR: ..."` strings rather than raising, consistent with the rest of the codebase.

---

## Deviations from the reference (and their impact)

1. **Added defensive guards** for empty `response.candidates` and `content is None` (`agent.py:111`, `:114`). The reference indexes `candidates[0]` and appends `candidate.content` unguarded. This is a genuine hardening and is consistent with the existing error-string convention — a net improvement, low risk.

2. **Added typing ceremony:** `from typing import Any, Callable, cast`, the `TOOL_FUNCTIONS: dict[str, Callable[..., object]]` annotation, and `tools=cast("list[Any]", TOOLS)` with comments citing mypy ("mypy stays happy"). **`mypy` is not in the project toolchain** — `pyproject.toml` declares only `pytest`/`pytest-asyncio` under `dev`, and the repo's explicit ethos is minimalist ("a ~200-line Gemini coding agent", "no framework magic"). The reference deliberately writes `tools=TOOLS` with no cast and no guards. This is mild over-engineering: real ceremony added to satisfy a checker the project doesn't run. Not wrong, and reasonable people ship the guarded version — but it trades a little of the reference's pedagogical clarity for type-cleanliness the repo doesn't require.

3. **Partial/inconsistent typing.** After introducing type annotations, `on_event` and the inner `emit(event)` remain untyped while local variables (`contents`, `response_parts`, `result`) are annotated. The typing effort is applied halfway.

---

## Blast radius / coupling

- **Default model id is a magic string duplicated across two files:** `gemini-3.5-flash` in `agent.py:80` and `verify.sh`. There is no shared constant, so the two must be changed in lockstep. This coupling pre-existed (the reference duplicated `gemini-2.5-flash` the same way), but this change has now *diverged the default from the reference* (`2.5` → `3.5`). **Action:** confirm `gemini-3.5-flash` is a valid model id — if it is not, both the `verify.sh` pre-flight and the agent's default path break out of the box, and the failure surfaces only at runtime.
- Otherwise the change is self-contained. It couples only to the Gemini SDK surface already used by the reference, and to the `on_event` dict-event shape the CLI already expects.

---

## Rating

**sound.**

The core architecture is the right one, matches the repo's own reference pattern, keeps responsibilities in the correct layers, and preserves the error-handling convention. The only design-level critiques are the type-hardening ceremony (out of step with the codebase's stated minimalism and its actual toolchain) and the duplicated/diverged default model constant — neither rises to the level of rework.

### Suggested follow-ups (optional, non-blocking)

1. Verify the `gemini-3.5-flash` model id; consider hoisting the default into one shared location instead of duplicating it in `agent.py` and `verify.sh`.
2. Decide whether mypy is actually part of this project. If not, drop the `cast`/typing ceremony to match the reference's clarity; if yes, add it to `pyproject.toml` and finish typing `on_event`/`emit`.
