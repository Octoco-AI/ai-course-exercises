import { runAgent as runReferenceAgent } from "../src/reference/agent.js";
import { ReferenceTools } from "../src/reference/tools.js";
import { runAgent as runStarterAgent } from "../src/starter/agent.js";
import { StarterTools } from "../src/starter/tools.js";
import type { Tools } from "../src/shared/types.js";

/**
 * Chooses which implementation the tests exercise.
 *
 * **Defaults to your code** — both the tools and the loop. Set
 * `TINY_AGENT_IMPL=reference` to run the same suite against the worked solution,
 * useful to confirm the tests themselves are sane, or to see green before you
 * start.
 *
 *     npm test                 # tests YOUR code
 *     npm run test:reference   # tests the worked solution
 *
 * The Python version of this exercise imports the reference implementation when
 * it is present and falls back to the starter, which means the suite goes green
 * against code the attendee never wrote until they hand-edit the import. This is
 * that bug fixed: here the default is always your own code.
 */
function selectedImpl(): "starter" | "reference" {
  const impl = process.env["TINY_AGENT_IMPL"]?.trim().toLowerCase();

  switch (impl) {
    case "reference":
      return "reference";
    case "starter":
    case undefined:
    case "":
      return "starter";
    default:
      throw new Error(`TINY_AGENT_IMPL must be 'starter' or 'reference', got '${impl}'.`);
  }
}

/** The tool implementation under test. */
export function createTools(sandboxRoot: string): Tools {
  return selectedImpl() === "reference"
    ? new ReferenceTools(sandboxRoot)
    : new StarterTools(sandboxRoot);
}

/** The agent loop under test — same switch, so step 1 gets a test suite too. */
export function selectRunAgent(): typeof runReferenceAgent {
  return selectedImpl() === "reference" ? runReferenceAgent : runStarterAgent;
}
