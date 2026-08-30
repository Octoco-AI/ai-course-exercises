/**
 * The three file-system tools the agent can call.
 *
 * Both `src/starter/tools.ts` and `src/reference/tools.ts` implement this, which
 * is how the test suite can point at either one (see `TINY_AGENT_IMPL` in the
 * README).
 *
 * Note the return types: every method returns a value, and failures come back as
 * strings starting with "ERROR:". Nothing throws. That is deliberate — the model
 * reads the error text and self-corrects; an exception just kills the loop. It
 * is the single most important contract in this file.
 */
export interface Tools {
  /** Read a UTF-8 text file and return its contents. */
  readFile(path: string): string;

  /** List entries in a directory. Directory names end with "/". */
  listFiles(path?: string): ListResult;

  /** Replace `oldStr` with `newStr`, exactly once. */
  editFile(path: string, oldStr: string, newStr: string): string;
}

/**
 * Result of {@link Tools.listFiles} — either entries, or an error string.
 *
 * The Python original returns a single-element `["ERROR: ..."]` list on failure
 * so the return type never changes. That is a Python-typing workaround; a
 * discriminated union says the same thing honestly here. What carries over
 * unchanged is that the model still receives a plain string describing the
 * failure — see {@link listResultToModelString}.
 */
export type ListResult =
  | { ok: true; entries: string[] }
  | { ok: false; error: string };

/** Flatten a list result to what the model sees: the entries, or the error text. */
export function listResultToModelString(result: ListResult): string {
  return result.ok ? result.entries.join("\n") : result.error;
}

/**
 * What the agent loop reports as it runs.
 *
 * The observer hook exists so later modules have somewhere to attach: M12
 * (CI/CD/CE) traces from here, and M16 (context engineering) counts tokens from
 * here. Keep calling `onEvent` from your loop even when nothing is listening.
 */
export type AgentEvent =
  | { type: "turn_start"; turn: number }
  | { type: "tool_call"; name: string; args: Record<string, unknown> }
  | { type: "tool_result"; name: string; result: string }
  | { type: "final"; text: string; turns: number };

export type OnEvent = (event: AgentEvent) => void;
