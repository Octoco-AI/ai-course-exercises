import { PathSandbox } from "../shared/sandbox.js";
import type { ListResult, Tools } from "../shared/types.js";

/**
 * Three file-system tools the agent can call. YOU WRITE THESE.
 *
 * Safety model: every path must be resolved through {@link PathSandbox} and
 * rejected if it escapes. That helper is given to you — call
 * `this.sandbox.resolve(path)`, which returns either `{ ok: true, path }` or
 * `{ ok: false, error }`.
 *
 * **Return errors as strings starting with "ERROR:". Do not throw.** The model
 * reads the message and self-corrects; an exception kills the loop. This is the
 * contract the tests check hardest.
 *
 * The JSON schema the model sees lives in `src/shared/toolSchemas.ts` and is
 * already written for you. Read it before you start — it is the spec.
 */
export class StarterTools implements Tools {
  private readonly sandbox: PathSandbox;

  constructor(sandboxRoot: string) {
    this.sandbox = new PathSandbox(sandboxRoot);
  }

  // ---------------------------------------------------------------------------
  // STEP 2a — implement readFile
  // ---------------------------------------------------------------------------
  readFile(_target: string): string {
    // TODO: call this.sandbox.resolve(_target). If !ok, return the error string.
    // TODO: return "ERROR: '<path>' does not exist" if it isn't there.
    // TODO: return "ERROR: '<path>' is not a file" if it's a directory.
    // TODO: read it with fs.readFileSync(resolved.path, "utf8") and return it.
    //       Wrap the read so an I/O failure comes back as an ERROR string.
    throw new Error("Implement readFile for step 2a.");
  }

  // ---------------------------------------------------------------------------
  // STEP 2b — implement listFiles
  // ---------------------------------------------------------------------------
  listFiles(_target = "."): ListResult {
    // TODO: resolve + validate (does it exist? is it a directory?).
    //       Return { ok: false, error: "ERROR: ..." } on any failure.
    // TODO: read entries with fs.readdirSync(path, { withFileTypes: true }).
    // TODO: append "/" to directory names so the model can tell them apart.
    // TODO: sort them, return { ok: true, entries }.
    throw new Error("Implement listFiles for step 2b.");
  }

  // ---------------------------------------------------------------------------
  // STEP 2c — implement editFile
  // ---------------------------------------------------------------------------
  editFile(_target: string, _oldStr: string, _newStr: string): string {
    // TODO: resolve + validate (exists, is a file).
    // TODO: read the current content.
    // TODO: count occurrences of _oldStr.
    //         0        -> "ERROR: old_str not found in '<path>'"
    //         above 1  -> "ERROR: old_str appears <n> times in '<path>'; must be unique. ..."
    //       and in BOTH error cases leave the file untouched.
    // TODO: replace the single occurrence, write it back, return "OK: edited <path>".
    //
    // Watch out: String.prototype.replaceAll() replaces EVERY occurrence, and
    // .replace() with a string replaces only the first without telling you there
    // were others. The exactly-once rule exists to prevent both, and there is a
    // test for it.
    throw new Error("Implement editFile for step 2c.");
  }
}
