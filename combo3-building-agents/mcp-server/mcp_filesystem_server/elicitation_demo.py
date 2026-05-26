"""Elicitation demo — stretch goal for Combo 3 M5 Part B.

Elicitation is a client-offered MCP primitive: the server can ask the user
for additional input mid-tool-execution. Canonical use case: a destructive
operation that must confirm with the user before proceeding.

This module is deliberately separate from server.py because elicitation is
newer, has had API churn, and may need a small adjustment against whatever
mcp SDK version ships at workshop time. Flag this to attendees: "run the
main server first, then try the elicitation demo as a stretch."

Verify the current elicitation API against:
  https://modelcontextprotocol.io/specification
  https://github.com/modelcontextprotocol/python-sdk

Run this instead of server.py when demonstrating:
  python -m mcp_filesystem_server.elicitation_demo
"""

from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import Context, FastMCP

from .tools import _resolve


mcp = FastMCP(
    "filesystem-server-with-elicitation",
    instructions=(
        "Filesystem server that asks for user confirmation before destructive actions. "
        "Demonstrates the MCP Elicitation primitive."
    ),
)


@mcp.tool()
async def delete_file(path: str, ctx: Context) -> str:
    """Delete a file — requires explicit user confirmation via Elicitation.

    Args:
        path: File path relative to the server's working directory.
    """
    resolved = _resolve(path)
    if isinstance(resolved, str):
        return resolved
    if not resolved.exists():
        return f"ERROR: {path!r} does not exist"
    if not resolved.is_file():
        return f"ERROR: {path!r} is not a file"

    # --- Elicitation: ask the user to confirm before we delete. ---
    #
    # The exact API is evolving. As of the MCP 2025-11-25 spec and the
    # mcp python SDK v1.x, the server calls `ctx.elicit()` with a message and
    # a schema describing the expected response. The client presents a form
    # to the user and returns the submitted value.
    #
    # If this signature drifts in a newer SDK, adjust to match. The concept
    # stays the same: server pauses, user responds, server continues.
    try:
        response = await ctx.elicit(
            message=f"Really delete {path!r}?",
            schema={
                "type": "object",
                "properties": {
                    "confirm": {
                        "type": "boolean",
                        "title": "Confirm deletion",
                        "description": "Set to true to delete this file.",
                    }
                },
                "required": ["confirm"],
            },
        )
    except AttributeError:
        # Older SDKs don't expose ctx.elicit.
        return (
            "ERROR: this server was built against an MCP SDK version that does "
            "not yet support elicitation. Update mcp to >=1.0 and retry."
        )
    except Exception as exc:  # noqa: BLE001
        return f"ERROR: elicitation failed: {type(exc).__name__}: {exc}"

    confirm = bool(getattr(response, "confirm", False) or (response or {}).get("confirm"))
    if not confirm:
        return "Aborted: user did not confirm deletion."

    resolved.unlink()
    return f"OK: deleted {path}"


@mcp.tool()
def read_file(path: str) -> str:
    """Read a file — non-destructive, no elicitation needed.

    Included so the demo server has a normal tool alongside the destructive one,
    which is a realistic shape for a production server.
    """
    from .tools import read_file as _read_file
    return _read_file(path)


def main() -> None:
    """Run the demo server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
