import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import type { GenerateContentResponse, GoogleGenAI } from "@google/genai";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { runAgent } from "../src/reference/agent.js";
import { ReferenceTools } from "../src/reference/tools.js";

/**
 * The loop's contract, tested offline against a canned model.
 *
 * These cover the three mistakes the facilitator notes say account for most
 * failures in the room: forgetting to append the model's own turn, sending tool
 * results under the wrong role, and never terminating.
 *
 * They need no API key and cost nothing — a stubbed `generateContent` replays
 * scripted turns and records what the loop sent back.
 *
 * They run against the REFERENCE loop, because the starter's is a stub. Once you
 * have written yours, swap the import at the top to `../src/starter/agent.js`
 * and watch them go green.
 */

/** A canned model that replays scripted turns and records every request. */
function fakeGemini(turns: GenerateContentResponse[]) {
  const requests: Array<Record<string, unknown>> = [];
  const queue = [...turns];

  const generateContent = vi.fn(async (request: Record<string, unknown>) => {
    requests.push(structuredClone(request));

    const next = queue.shift();
    if (!next) {
      throw new Error("fakeGemini ran out of scripted responses — the loop asked for more turns than expected.");
    }
    return next;
  });

  return {
    ai: { models: { generateContent } } as unknown as GoogleGenAI,
    requests,
    generateContent,
  };
}

const textTurn = (text: string) =>
  ({ candidates: [{ content: { role: "model", parts: [{ text }] } }] }) as GenerateContentResponse;

const toolCallTurn = (name: string, args: Record<string, unknown>) =>
  ({
    candidates: [{ content: { role: "model", parts: [{ functionCall: { name, args } }] } }],
  }) as GenerateContentResponse;

/** Read the `contents` array the loop sent on a given request. */
function contentsOf(request: Record<string, unknown>) {
  return request["contents"] as Array<{ role: string; parts: Array<Record<string, unknown>> }>;
}

describe("agent loop", () => {
  let sandbox: string;
  let tools: ReferenceTools;

  beforeEach(() => {
    sandbox = fs.mkdtempSync(path.join(os.tmpdir(), "tiny-agent-loop-"));
    fs.writeFileSync(path.join(sandbox, "hello.txt"), "hello world\n");
    tools = new ReferenceTools(sandbox);
  });

  afterEach(() => {
    fs.rmSync(sandbox, { recursive: true, force: true });
  });

  it("returns text when the model makes no tool call", async () => {
    const { ai, requests } = fakeGemini([textTurn("All done.")]);

    const final = await runAgent("do the thing", tools, ai, { model: "fake-model" });

    expect(final).toBe("All done.");
    expect(requests).toHaveLength(1);
  });

  it("runs a tool then returns the final text", async () => {
    const { ai, requests } = fakeGemini([
      toolCallTurn("read_file", { path: "hello.txt" }),
      textTurn("The file says hello world."),
    ]);

    const final = await runAgent("read it", tools, ai, { model: "fake-model" });

    expect(final).toBe("The file says hello world.");
    expect(requests).toHaveLength(2);
    // The second request must carry the tool's output back to the model.
    expect(JSON.stringify(requests[1])).toContain("hello world");
  });

  it("appends the model's own turn before the tool result", async () => {
    // The single most-forgotten line in this exercise. If the model's turn isn't
    // appended, the model never sees that it already asked, and asks again forever.
    const { ai, requests } = fakeGemini([
      toolCallTurn("read_file", { path: "hello.txt" }),
      textTurn("done"),
    ]);

    await runAgent("read it", tools, ai, { model: "fake-model" });

    const contents = contentsOf(requests[1]!);
    expect(contents).toHaveLength(3); // user prompt, model turn, tool result
    expect(contents[0]!.role).toBe("user");
    expect(contents[1]!.role).toBe("model");
    expect(contents[1]!.parts[0]).toHaveProperty("functionCall");
  });

  it("sends tool results with the user role", async () => {
    // Not "tool", not "function". About 15% of pairs try one of those.
    const { ai, requests } = fakeGemini([
      toolCallTurn("read_file", { path: "hello.txt" }),
      textTurn("done"),
    ]);

    await runAgent("read it", tools, ai, { model: "fake-model" });

    const toolTurn = contentsOf(requests[1]!)[2]!;
    expect(toolTurn.role).toBe("user");
    expect(toolTurn.parts[0]).toHaveProperty("functionResponse");
  });

  it("passes tool errors back to the model as strings", async () => {
    // A tool failure must not kill the loop — the model gets to read it and retry.
    const { ai, requests } = fakeGemini([
      toolCallTurn("read_file", { path: "nope.txt" }),
      textTurn("That file doesn't exist."),
    ]);

    const final = await runAgent("read it", tools, ai, { model: "fake-model" });

    expect(final).toBe("That file doesn't exist.");
    expect(JSON.stringify(requests[1])).toContain("ERROR:");
    expect(JSON.stringify(requests[1])).toContain("does not exist");
  });

  it("reports an unknown tool rather than throwing", async () => {
    const { ai, requests } = fakeGemini([
      toolCallTurn("delete_everything", { path: "." }),
      textTurn("I can't do that."),
    ]);

    const final = await runAgent("wreck it", tools, ai, { model: "fake-model" });

    expect(final).toBe("I can't do that.");
    expect(JSON.stringify(requests[1])).toContain("unknown tool");
  });

  it("disables automatic function calling", async () => {
    // If this is ever false, you don't have an agent — you have a function
    // Google called on your behalf.
    const { ai, requests } = fakeGemini([textTurn("done")]);

    await runAgent("anything", tools, ai, { model: "fake-model" });

    const config = requests[0]!["config"] as Record<string, unknown>;
    expect(config["automaticFunctionCalling"]).toEqual({ disable: true });
  });

  it("stops at maxTurns", async () => {
    // A model that never stops calling tools must not loop forever.
    const turns = Array.from({ length: 3 }, () => toolCallTurn("read_file", { path: "hello.txt" }));
    const { ai, requests } = fakeGemini(turns);

    const final = await runAgent("loop forever", tools, ai, { model: "fake-model", maxTurns: 3 });

    expect(final).toMatch(/^ERROR:/);
    expect(final).toContain("did not finish within 3 turns");
    expect(requests).toHaveLength(3);
  });
});
