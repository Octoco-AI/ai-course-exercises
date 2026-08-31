import fs from "node:fs";
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

  /**
   * The root with symlinks resolved. Containment is decided against this rather
   * than `root`, because a real path can only be compared against another real
   * path: on macOS `os.tmpdir()` is itself behind a symlink, so checking a
   * resolved path against a lexical root would reject the sandbox's own files.
   */
  private readonly realRoot: string;

  constructor(root: string) {
    this.root = path.resolve(root);
    this.realRoot = realPath(this.root) ?? this.root;
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

    // First pass, purely textual: catches '..' traversal and absolute paths
    // pointing elsewhere, which is most of what a confused model sends.
    if (!isInside(this.root, candidate)) {
      return {
        ok: false,
        error: `ERROR: path '${target}' is outside the sandbox (${this.root})`,
      };
    }

    // Second pass, following symlinks. `path.resolve` is textual, so a symlink
    // *inside* the sandbox may point anywhere on disk and still sail through the
    // check above — and `fs` will happily follow it. Decide on the real path.
    const real = realPath(candidate);
    if (real !== null && !isInside(this.realRoot, real)) {
      return {
        ok: false,
        error:
          `ERROR: path '${target}' is a symlink leading outside the sandbox ` +
          `(${this.root})`,
      };
    }

    return { ok: true, path: candidate };
  }
}

/** True when `candidate` is `root` itself, or something underneath it. */
function isInside(root: string, candidate: string): boolean {
  if (candidate === root) return true;

  // Compare against root + separator, never a bare prefix: a plain
  // startsWith() would let "/tmp/sandbox-evil" pass as inside "/tmp/sandbox".
  return candidate.startsWith(root + path.sep);
}

/**
 * `target` with every symlink along it resolved.
 *
 * A path that does not exist yet still has to be checked — its parent may be the
 * symlink — so walk up to the nearest ancestor that does exist, resolve that,
 * and re-attach the tail. Returns null only if nothing resolves at all.
 */
function realPath(target: string): string | null {
  let existing = target;
  const missing: string[] = [];

  for (;;) {
    try {
      return path.join(fs.realpathSync(existing), ...missing);
    } catch {
      const parent = path.dirname(existing);
      if (parent === existing) return null; // reached the filesystem root
      missing.unshift(path.basename(existing));
      existing = parent;
    }
  }
}
