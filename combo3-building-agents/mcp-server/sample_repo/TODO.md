# Things to ask an MCP client to do (with this server attached)

For use from Claude Desktop, Claude Code, or any MCP client.

## Consume-the-server exercises (Part A)

1. *"What tools does the filesystem server expose?"*
   - Checks that the server is connected and introspection works.
2. *"List the files in the sample_repo directory."*
   - Verifies `list_files`.
3. *"Read `recipes.md` and summarise what's in it."*
   - Verifies `read_file`.
4. *"Add a new H2 section to `recipes.md` titled 'On sandboxing well' with one paragraph."*
   - Verifies `edit_file` for an append-style change.
5. *"Fetch the sandbox-root resource and tell me where the server is rooted."*
   - Verifies resources.

## Build-your-own-server exercise (Part B)

Part B isn't done here — you build a **new**, separate MCP server in your
agent's own repo (`mcp_my_server/__init__.py` + `mcp_my_server/server.py`),
wrapping ONE tool from an earlier module (Track A: `search_docs` or
`edit_file`; Track B: `search_kb` or `draft_reply`). Module 35's
`exercise.adoc` (Part B) has the full code sample. This file's server
(`mcp_filesystem_server/`) is reference material to read alongside your
own — don't edit it.

After you've written your server:

1. Start it (or point Claude Desktop / Claude Code at it via config).
2. Ask your client to use the new tool.
3. Notice the client config only names the server — the tool itself is
   discovered automatically.

## Elicitation exercise (stretch)

Run the alternative entrypoint `python -m mcp_filesystem_server.elicitation_demo` instead of the main server. Ask the client to delete a file:

6. *"Delete `recipes.md`."*
   - Expected: the client prompts you to confirm; on confirmation, the file is deleted; on decline, it stays.
