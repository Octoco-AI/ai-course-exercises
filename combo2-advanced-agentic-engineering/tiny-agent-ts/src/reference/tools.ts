import fs from "node:fs";
import path from "node:path";

import { PathSandbox } from "../shared/sandbox.js";
import type { ListResult, Tools } from "../shared/types.js";

/**
 * Three file-system tools the agent can call — complete worked solution.
 *
 * Mirrors Thorsten Ball's ampcode walkthrough:
 * https://ampcode.com/how-to-build-an-agent
 *
 * Safety model: every path is resolved against the sandbox root and rejected if
 * it escapes. No ".." traversal, no absolute paths outside the sandbox.
 *
 * Errors are RETURNED as strings, never thrown. The model reads the message and
 * self-corrects; a stack trace just confuses it and kills the loop.
 */
export class ReferenceTools implements Tools {
  private readonly sandbox: PathSandbox;

  constructor(sandboxRoot: string) {
    this.sandbox = new PathSandbox(sandboxRoot);
  }

  readFile(target: string): string {
    const resolved = this.sandbox.resolve(target);
    if (!resolved.ok) return resolved.error;

    const stat = statOrNull(resolved.path);
    if (stat === null) return `ERROR: '${target}' does not exist`;
    if (stat.isDirectory()) return `ERROR: '${target}' is not a file`;

    try {
      return fs.readFileSync(resolved.path, "utf8");
    } catch (err) {
      return `ERROR: could not read '${target}': ${(err as Error).message}`;
    }
  }

  listFiles(target = "."): ListResult {
    const resolved = this.sandbox.resolve(target);
    if (!resolved.ok) return { ok: false, error: resolved.error };

    const stat = statOrNull(resolved.path);
    if (stat === null) return { ok: false, error: `ERROR: '${target}' does not exist` };
    if (!stat.isDirectory()) return { ok: false, error: `ERROR: '${target}' is not a directory` };

    try {
      const entries = fs
        .readdirSync(resolved.path, { withFileTypes: true })
        .map((entry) => (entry.isDirectory() ? `${entry.name}/` : entry.name))
        .sort();
      return { ok: true, entries };
    } catch (err) {
      return { ok: false, error: `ERROR: could not list '${target}': ${(err as Error).message}` };
    }
  }

  editFile(target: string, oldStr: string, newStr: string): string {
    const resolved = this.sandbox.resolve(target);
    if (!resolved.ok) return resolved.error;

    const stat = statOrNull(resolved.path);
    if (stat === null) return `ERROR: '${target}' does not exist`;
    if (stat.isDirectory()) return `ERROR: '${target}' is not a file`;

    let content: string;
    try {
      content = fs.readFileSync(resolved.path, "utf8");
    } catch (err) {
      return `ERROR: could not read '${target}': ${(err as Error).message}`;
    }

    const count = countOccurrences(content, oldStr);
    if (count === 0) return `ERROR: old_str not found in '${target}'`;
    if (count > 1) {
      return (
        `ERROR: old_str appears ${count} times in '${target}'; must be unique. ` +
        "Add more surrounding context to old_str so it matches exactly once."
      );
    }

    // Note: NOT content.replaceAll — the exactly-once rule is the whole point.
    const index = content.indexOf(oldStr);
    const updated = content.slice(0, index) + newStr + content.slice(index + oldStr.length);

    try {
      fs.writeFileSync(resolved.path, updated, "utf8");
    } catch (err) {
      return `ERROR: could not write '${target}': ${(err as Error).message}`;
    }

    return `OK: edited ${path.normalize(target)}`;
  }
}

function statOrNull(target: string): fs.Stats | null {
  try {
    return fs.statSync(target);
  } catch {
    return null;
  }
}

/** Count non-overlapping occurrences. An empty needle counts as zero. */
function countOccurrences(haystack: string, needle: string): number {
  if (needle.length === 0) return 0;

  let count = 0;
  let index = haystack.indexOf(needle);
  while (index !== -1) {
    count += 1;
    index = haystack.indexOf(needle, index + needle.length);
  }
  return count;
}
