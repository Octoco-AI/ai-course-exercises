# MCP Filesystem Server — Combo 3 M5 reference

A minimal Model Context Protocol server exposing three filesystem tools: `read_file`, `list_files`, `edit_file`. Built with the official `mcp` Python SDK's `FastMCP` helper. Runs over stdio by default; HTTP and SSE transports are one-line changes.

The point of this example is the **wrap, don't rewrite** pattern: the three tools are identical to the ones you built in Combo 1 M1 (tiny-agent). All that's different is three `@mcp.tool()` decorators and a `mcp.run()` call.

---

## Quick start

```bash
# From this directory
python3 -m venv .venv
source .venv/bin/activate                # or .venv\Scripts\activate on Windows
pip install -e '.[dev]'
./verify.sh
```

Then, from `sample_repo/`:

```bash
cd sample_repo
python -m mcp_filesystem_server.server
```

The server will sit on stdin/stdout waiting for an MCP client to speak to it. That's normal — test it with the MCP Inspector or hook it into Claude Code.

---

## Poking at the server with MCP Inspector

[MCP Inspector](https://github.com/modelcontextprotocol/inspector) is a browser UI for introspecting and calling MCP servers. No install — run via `npx`:

```bash
cd sample_repo
npx @modelcontextprotocol/inspector python -m mcp_filesystem_server.server
```

In the UI:

1. You'll see three tools listed: `read_file`, `list_files`, `edit_file`. Each shows its description and JSON schema.
2. Call `list_files` with `path: "."` — you'll see the sample-repo contents.
3. Call `read_file` with `path: "recipes.md"`.
4. There's also a resource at `server://sandbox-root` — click through to fetch it.

This is the "consume an MCP server" experience attendees go through in M5 Part A.

---

## Adding the server to Claude Code

1. Copy `claude-code-mcp-config.json.example` to `.claude/mcp.json` in any project where you want the server available.
2. Edit the two `/ABSOLUTE/PATH/TO/` placeholders to point at this repo's `sample_repo/` and `mcp-server/` directories.
3. Start Claude Code in that project. Ask it to *"list the files in the workshop-filesystem sandbox"* — it should delegate to the MCP server.

---

## Adding the server to Claude Desktop

Add a similar block to your Claude Desktop config (path differs by OS):

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "workshop-filesystem": {
      "command": "python",
      "args": ["-m", "mcp_filesystem_server.server"],
      "cwd": "/ABSOLUTE/PATH/TO/mcp-server/sample_repo",
      "env": { "PYTHONPATH": "/ABSOLUTE/PATH/TO/mcp-server" }
    }
  }
}
```

Restart Claude Desktop. Open a new chat. The server will appear in the MCP servers list at the bottom-left.

---

## What this example does NOT do

- **Does not speak HTTP out of the box.** It's stdio-only, which is the simplest and most common transport. Switch by setting `MCP_TRANSPORT=streamable-http` before running — but you'll need to add network config (port, auth).
- **Does not implement OAuth or advanced auth.** For stdio that's fine; for HTTP exposure you should secure it.
- **Does not demonstrate Sampling.** Sampling is the other direction (the server asks the client for LLM inference). Separate exercise.
- **Does not demonstrate all 6 MCP utilities.** Just tools and one resource. Elicitation lives in a separate `elicitation_demo.py` module — see below.

---

## Stretch: Elicitation demo

Elicitation is a newer MCP primitive that lets a server ask the user for more information mid-tool-execution. A second entrypoint (`mcp_filesystem_server.elicitation_demo`) shows it in action with a `delete_file` tool that confirms before deleting.

To run:

```bash
cd sample_repo
python -m mcp_filesystem_server.elicitation_demo
```

Then ask the client (Inspector / Claude Desktop / Claude Code) to *"delete hello.py"*. If the client supports elicitation, it prompts you to confirm; on confirmation the file is deleted, on decline it's preserved.

⚠️ **The exact elicitation API is evolving.** The `elicitation_demo.py` module is written against the MCP spec 2025-11-25 and mcp-python-sdk v1.x (fetched 2026-04-21). If the SDK has moved since, the call signature inside `delete_file` may need a small adjustment. See `https://github.com/modelcontextprotocol/python-sdk` for the current shape.

---

## File structure

```
mcp-server/
├── README.md                  ← you are here
├── FACILITATOR.md             ← notes for the workshop facilitator
├── pyproject.toml
├── verify.sh
├── claude-code-mcp-config.json.example
├── mcp_filesystem_server/
│   ├── server.py              ← the main MCP server (3 tools + 1 resource)
│   ├── tools.py               ← tool implementations (identical to tiny-agent/)
│   └── elicitation_demo.py    ← stretch: server that asks for confirmation
├── sample_repo/               ← what the server operates on
│   ├── README.md
│   ├── hello.py
│   ├── recipes.md
│   └── TODO.md                ← prompts to try against the server
└── tests/
    └── test_tools.py
```

---

## Further reading

- **MCP introduction and spec**: https://modelcontextprotocol.io
- **`modelcontextprotocol/python-sdk`**: https://github.com/modelcontextprotocol/python-sdk
- **MCP Inspector**: https://github.com/modelcontextprotocol/inspector
- **ampcode's "How to build an agent"** (for the tool shape this wraps): https://ampcode.com/how-to-build-an-agent
