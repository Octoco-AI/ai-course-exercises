import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { afterEach, beforeEach, describe, expect, it } from "vitest";

import type { Tools } from "../src/shared/types.js";
import { createTools } from "./impl.js";

/**
 * The contract your tool implementations must satisfy.
 *
 * These 15 tests ARE the spec — read them before you write anything. They are
 * also a preview of M11: notice that each one names a behaviour and asserts on
 * it, rather than checking the implementation.
 *
 *     npm test
 */
describe("tools", () => {
  let sandbox: string;
  let tools: Tools;
  let outsideFiles: string[];

  beforeEach(() => {
    // A fresh temp directory per test, seeded the same way as the Python
    // fixture: one file, one nested directory with a file in it.
    sandbox = fs.mkdtempSync(path.join(os.tmpdir(), "tiny-agent-tests-"));

    fs.writeFileSync(path.join(sandbox, "hello.txt"), "hello world\n");
    fs.mkdirSync(path.join(sandbox, "nested"));
    fs.writeFileSync(path.join(sandbox, "nested", "deep.txt"), "deep content\n");

    tools = createTools(sandbox);
    outsideFiles = [];
  });

  afterEach(() => {
    fs.rmSync(sandbox, { recursive: true, force: true });
    for (const target of outsideFiles) fs.rmSync(target, { force: true });
  });

  const read = (relative: string) => fs.readFileSync(path.join(sandbox, relative), "utf8");

  /**
   * Create a symlink, or report that the OS wouldn't allow it — Windows needs
   * developer mode or admin rights. The escape tests below skip there rather
   * than fail for a reason that has nothing to do with your code.
   */
  const trySymlink = (target: string, linkPath: string): boolean => {
    try {
      fs.symlinkSync(target, linkPath);
      return true;
    } catch {
      return false;
    }
  };

  /** A file outside the sandbox, cleaned up after the test that made it. */
  const makeOutsideFile = (tag: string) => {
    const target = path.join(os.tmpdir(), `tiny-agent-outside-${tag}-${process.pid}.txt`);
    fs.writeFileSync(target, "secret\n");
    outsideFiles.push(target);
    return target;
  };

  // ---- readFile -------------------------------------------------------------

  it("readFile: success", () => {
    expect(tools.readFile("hello.txt")).toBe("hello world\n");
  });

  it("readFile: nested", () => {
    expect(tools.readFile("nested/deep.txt")).toBe("deep content\n");
  });

  it("readFile: missing", () => {
    const result = tools.readFile("does-not-exist.txt");
    expect(result).toMatch(/^ERROR:/);
    expect(result).toContain("does not exist");
  });

  it("readFile: directory is not a file", () => {
    const result = tools.readFile("nested");
    expect(result).toMatch(/^ERROR:/);
    expect(result).toContain("not a file");
  });

  it("readFile: escape attempt", () => {
    // The guard. If this ever goes green by accident, the sandbox is broken.
    const result = tools.readFile("../outside.txt");
    expect(result).toMatch(/^ERROR:/);
    expect(result).toContain("outside");
  });

  it("readFile: symlink escape attempt", () => {
    // The second guard, and the subtler one. path.resolve() is textual, so a
    // symlink *inside* the sandbox pointing anywhere on disk passes a lexical
    // containment check — and then fs follows it. PathSandbox resolves the real
    // path before deciding, which is why calling it is not optional.
    const outside = makeOutsideFile("read");
    if (!trySymlink(outside, path.join(sandbox, "link.txt"))) return;

    const result = tools.readFile("link.txt");
    expect(result).toMatch(/^ERROR:/);
    expect(result).toContain("outside");
  });

  // ---- listFiles ------------------------------------------------------------

  it("listFiles: root", () => {
    const result = tools.listFiles(".");
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.entries).toContain("hello.txt");
    expect(result.entries).toContain("nested/");
  });

  it("listFiles: nested", () => {
    const result = tools.listFiles("nested");
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.entries).toEqual(["deep.txt"]);
  });

  it("listFiles: missing", () => {
    const result = tools.listFiles("no-such-dir");
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error).toMatch(/^ERROR:/);
  });

  it("listFiles: on a file", () => {
    const result = tools.listFiles("hello.txt");
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error).toMatch(/^ERROR:/);
  });

  // ---- editFile -------------------------------------------------------------

  it("editFile: success", () => {
    const result = tools.editFile("hello.txt", "hello", "hi");
    expect(result).toMatch(/^OK:/);
    expect(read("hello.txt")).toBe("hi world\n");
  });

  it("editFile: missing old_str", () => {
    const result = tools.editFile("hello.txt", "goodbye", "hi");
    expect(result).toMatch(/^ERROR:/);
    expect(result).toContain("not found");
  });

  it("editFile: non-unique old_str", () => {
    fs.writeFileSync(path.join(sandbox, "repeated.txt"), "foo bar foo baz\n");

    const result = tools.editFile("repeated.txt", "foo", "qux");
    expect(result).toMatch(/^ERROR:/);
    expect(result).toContain("2 times");

    // The file must NOT have been modified on a non-unique match. This is the
    // test that catches a naive replaceAll().
    expect(read("repeated.txt")).toBe("foo bar foo baz\n");
  });

  it("editFile: preserves the file on error", () => {
    const original = read("hello.txt");
    tools.editFile("hello.txt", "nope", "yep");
    expect(read("hello.txt")).toBe(original);
  });

  it("editFile: will not write through a symlink out of the sandbox", () => {
    const outside = makeOutsideFile("edit");
    if (!trySymlink(outside, path.join(sandbox, "link.txt"))) return;

    const result = tools.editFile("link.txt", "secret", "pwned");
    expect(result).toMatch(/^ERROR:/);
    expect(fs.readFileSync(outside, "utf8")).toBe("secret\n");
  });
});
