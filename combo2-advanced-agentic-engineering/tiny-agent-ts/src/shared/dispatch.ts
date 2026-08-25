import { EDIT_FILE, LIST_FILES, READ_FILE } from "./toolSchemas.js";
import { listResultToModelString, type Tools } from "./types.js";

/**
 * Route one function call to a tool. GIVEN — call it, don't rewrite it.
 *
 * Every failure path returns a string. Nothing thrown here reaches the loop —
 * that is the whole point.
 */
export function dispatch(tools: Tools, name: string, args: Record<string, unknown>): string {
  try {
    switch (name) {
      case READ_FILE:
        return tools.readFile(requiredArg(args, "path"));
      case LIST_FILES:
        return listResultToModelString(tools.listFiles(optionalArg(args, "path") ?? "."));
      case EDIT_FILE:
        return tools.editFile(
          requiredArg(args, "path"),
          requiredArg(args, "old_str"),
          requiredArg(args, "new_str"),
        );
      default:
        return `ERROR: unknown tool '${name}'`;
    }
  } catch (err) {
    if (err instanceof TypeError) {
      return `ERROR: bad arguments to ${name}: ${err.message}`;
    }
    // Surface any tool failure to the model rather than killing the loop.
    const e = err as Error;
    return `ERROR: ${e.name ?? "Error"}: ${e.message ?? String(err)}`;
  }
}

function requiredArg(args: Record<string, unknown>, name: string): string {
  const value = optionalArg(args, name);
  if (value === undefined) {
    throw new TypeError(`missing required argument '${name}'`);
  }
  return value;
}

function optionalArg(args: Record<string, unknown>, name: string): string | undefined {
  const value = args[name];
  return typeof value === "string" ? value : undefined;
}
