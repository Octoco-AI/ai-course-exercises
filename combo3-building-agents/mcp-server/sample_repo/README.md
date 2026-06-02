# Sample Repo

Tiny sandbox for the MCP server to operate on. The server resolves all paths against whatever directory you started it in, so **start the server from inside this directory** when testing:

```bash
cd sample_repo
python -m mcp_filesystem_server.server
```

## Contents

- `hello.py` — trivial greeting.
- `recipes.md` — a few notes the LLM can read.
- `TODO.md` — prompts you can give a client to drive the server.
