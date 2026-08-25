import path from "node:path";

/**
 * Resolves a caller-supplied path against a fixed root, refusing anything that
 * escapes it. This helper is GIVEN to you — it does the path-safety check so you
 * can focus on the tool logic.
 *
 * The Python original captures the sandbox root at import time in a module
 * global. Here the root is passed in instead: same idea, and it makes the tests
 * straightforward (they hand in a temp directory rather than patching a global).
 */
export class PathSandbox {
  readonly root: string;

  constructor(root: string) {
    this.root = path.resolve(root);
  }

  /**
   * Resolve `target` inside the sandbox.
   *
   * @returns the absolute path, or an error string starting with "ERROR:".
   */
  resolve(target: string): { ok: true; path: string } | { ok: false; error: string } {
    let candidate: string;
    try {
      candidate = path.resolve(this.root, target);
    } catch (err) {
      return { ok: false, error: `ERROR: could not resolve path '${target}': ${String(err)}` };
    }

    if (!this.isInsideRoot(candidate)) {
      return { ok: false, error: `ERROR: path '${target}' is outside the sandbox (${this.root})` };
    }

    return { ok: true, path: candidate };
  }

  private isInsideRoot(candidate: string): boolean {
    if (candidate === this.root) return true;

    // Compare against root + separator, never a bare prefix: a plain
    // startsWith() would let "/tmp/sandbox-evil" pass as inside "/tmp/sandbox".
    return candidate.startsWith(this.root + path.sep);
  }
}
