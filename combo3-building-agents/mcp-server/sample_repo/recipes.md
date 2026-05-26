# Sample notes

A few short notes for the server (and anyone calling it) to have something to read.

## On writing good tools

A good tool has a short, clear name, a docstring the LLM reads, and error messages the LLM can act on. Stack traces confuse the model; structured error strings let it self-correct.

## On sandboxing

Every path a tool accepts should be resolved against a known root and rejected if it escapes. Never trust a path.

## On the MCP protocol

Clients and servers speak JSON-RPC 2.0. The server exposes tools (callable), resources (read-only data), and prompts (reusable templates). The client decides which to pull into model context.

## On elicitation

A server can ask the user for additional input mid-tool-execution. Use it sparingly — only when the server genuinely needs input it can't derive from the current arguments. Overuse turns every tool call into a dialogue.
