"""A minimal MCP server exposing read_file, list_files, and edit_file.

This is what Combo 3 M5 Part A attendees CONSUME — the "existing server" we
supply. In Part B, attendees build their own server from scratch (or fork
this one and add a fourth custom tool).

The pattern demonstrated here:

  1. Start with tools that already work (from Combo 1 M1).
  2. Wrap them with ``@mcp.tool()``.
  3. Run with ``mcp.run()`` on stdio.

That's the entire "expose as MCP" transformation. Three decorators, no
rewrites, no schema authoring — the MCP SDK introspects the function
signature (name, docstring, type hints) the same way Gemini's SDK does.

Usage:

  # Direct:
  python -m mcp_filesystem_server.server

  # Via Claude Code:
  add this server to .claude/mcp.json (see claude-code-mcp-config.json.example)

  # Via Claude Desktop:
  add to ~/Library/Application Support/Claude/claude_desktop_config.json
  (see the README).

  # With MCP Inspector (hot-reload UI for poking at servers):
  npx @modelcontextprotocol/inspector python -m mcp_filesystem_server.server
"""

from __future__ import annotations

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .tools import edit_file as _edit_file
from .tools import list_files as _list_files
from .tools import read_file as _read_file


# ---- server setup ------------------------------------------------------------

# Instructions are shown to clients when they introspect the server. Keep them
# short and explicit about scope. Clients pass this to their model.
INSTRUCTIONS = """
A small filesystem server exposing three tools: read_file, list_files, edit_file.

All paths are resolved against the directory the server was started in and
cannot escape it. Errors are returned as strings beginning with "ERROR:" —
read the message and adjust; don't retry blindly.
""".strip()

mcp = FastMCP("filesystem-server", instructions=INSTRUCTIONS)


# ---- tools -------------------------------------------------------------------
#
# Each @mcp.tool() call takes the plain Python function and publishes it as
# an MCP tool. The SDK derives:
#
#   - tool name from the function name
#   - tool description from the docstring
#   - input schema from the type hints on parameters
#   - output handling from the return type annotation
#
# The underscore-prefixed imports above let us decorate without shadowing.


@mcp.tool()
def read_file(path: str) -> str:
    """Read a file and return its contents as a string.

    Args:
        path: File path relative to the server's working directory.
    """
    return _read_file(path)


@mcp.tool()
def list_files(path: str = ".") -> list[str]:
    """List entries in a directory.

    Args:
        path: Directory path relative to the server's working directory.
            Defaults to ".".
    """
    return _list_files(path)


@mcp.tool()
def edit_file(path: str, old_str: str, new_str: str) -> str:
    """Replace old_str with new_str in a file. old_str must appear exactly once.

    Args:
        path: File path relative to the server's working directory.
        old_str: Exact text to replace. Must be unique in the file.
        new_str: Replacement text.
    """
    return _edit_file(path, old_str, new_str)


# ---- a tiny resource, to show the pattern ------------------------------------
#
# Resources are read-only data the server exposes. Think "GET endpoints" that
# clients can fetch without using a tool. Useful for static config, schemas,
# or introspection info.


@mcp.resource("server://sandbox-root")
def sandbox_root_resource() -> str:
    """Return the absolute path of the directory this server is sandboxed to."""
    return str(Path.cwd().resolve())


# ---- entrypoint --------------------------------------------------------------


def main() -> None:
    """Run the server over stdio (the default and simplest transport)."""
    # FastMCP.run() blocks and handles the MCP protocol on stdin/stdout.
    # Use transport="streamable-http" for HTTP, or "sse" for Server-Sent Events.
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "stdio":
        mcp.run()
    else:
        mcp.run(transport=transport)


if __name__ == "__main__":
    main()
