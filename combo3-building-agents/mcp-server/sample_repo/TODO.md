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

## Build-your-own-tool exercises (Part B)

Open `mcp_filesystem_server/server.py` and add a fourth tool of your choice. Some candidates:

- `run_tests() -> str` — shell out to `pytest` and return the output.
- `grep(pattern: str, path: str = ".") -> list[str]` — find lines matching a regex.
- `word_count(path: str) -> int` — count words in a file.
- `search_recipes(query: str) -> list[str]` — a tiny dedicated search over the `recipes.md` file.

After you've added your tool:

1. Restart the server (or Claude Desktop / Claude Code).
2. Ask your client to use the new tool.
3. Notice that you didn't change the client config — just the server — and the new tool is immediately available.

## Elicitation exercise (stretch)

Run the alternative entrypoint `python -m mcp_filesystem_server.elicitation_demo` instead of the main server. Ask the client to delete a file:

6. *"Delete `recipes.md`."*
   - Expected: the client prompts you to confirm; on confirmation, the file is deleted; on decline, it stays.
