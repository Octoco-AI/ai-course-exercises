/**
 * Console entrypoint. GIVEN — no changes needed.
 *
 * Runs your starter implementation by default:
 *     npm run agent -- "List the files here"
 *
 * Or the worked solution:
 *     npm run agent:reference -- "List the files here"
 */
import { GoogleGenAI } from "@google/genai";
import "dotenv/config";

import { runAgent as runReference } from "./reference/agent.js";
import { ReferenceTools } from "./reference/tools.js";
import { runAgent as runStarter } from "./starter/agent.js";
import { StarterTools } from "./starter/tools.js";
import type { AgentEvent, Tools } from "./shared/types.js";

/** Print one line per meaningful action, so the loop is visible as it runs. */
function printEvent(event: AgentEvent): void {
  if (event.type === "tool_call") {
    const preview = Object.entries(event.args)
      .map(([key, value]) => `${key}=${JSON.stringify(value)}`)
      .join(", ");
    const truncated = preview.length > 120 ? `${preview.slice(0, 117)}...` : preview;
    console.log(`  -> ${event.name}(${truncated})`);
  } else if (event.type === "tool_result") {
    const result =
      event.result.length > 200 ? `${event.result.slice(0, 197)}...` : event.result;
    console.log(`     ${result.replace(/\n/g, " | ")}`);
  }
}

async function main(): Promise<number> {
  const args = process.argv.slice(2);
  if (args.length === 0) {
    console.error('Usage: npm run agent -- "<your prompt>"');
    return 1;
  }

  const apiKey = process.env["GOOGLE_API_KEY"];
  if (!apiKey || apiKey === "your_gemini_api_key_here") {
    console.error("ERROR: GOOGLE_API_KEY is not set. Copy .env.example to .env and paste your key.");
    return 2;
  }

  const useReference = process.env["TINY_AGENT_IMPL"] === "reference";

  // The sandbox root is wherever you started the agent — same rule as the
  // Python version, where it is Path.cwd().
  const root = process.cwd();
  const tools: Tools = useReference ? new ReferenceTools(root) : new StarterTools(root);
  const run = useReference ? runReference : runStarter;

  const ai = new GoogleGenAI({ apiKey });

  try {
    const final = await run(args.join(" "), tools, ai, { onEvent: printEvent });
    console.log();
    console.log(final);
    return 0;
  } catch (err) {
    console.error(`ERROR: ${(err as Error).message}`);
    return 3;
  }
}

process.exitCode = await main();
