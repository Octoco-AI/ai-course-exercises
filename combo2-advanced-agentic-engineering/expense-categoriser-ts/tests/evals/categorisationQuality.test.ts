import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import "dotenv/config";
import { beforeAll, describe, expect, it } from "vitest";

import { categorise } from "../../src/core.js";
import { GeminiClient } from "../../src/geminiClient.js";
import type { CategorisationOut } from "../../src/models.js";

/**
 * Layer 3 — the eval suite. This is the "third layer" from Herman's blog.
 *
 * Run locally:
 *     npm run test:evals
 *
 * In CI:
 *     .github/workflows/evals.yml runs this on every PR with the GOOGLE_API_KEY
 *     secret. A failing eval blocks the merge.
 *
 * What's being tested:
 *   1. **Acceptance accuracy** — across the golden dataset, the rate of "chose an
 *      acceptable category" must be >= ACCURACY_THRESHOLD.
 *   2. **Zero catastrophics** — no case may be categorised as one of its
 *      explicitly unacceptable categories. This is a hard gate.
 *   3. **Latency** — p95 per-request latency below a ceiling.
 *   4. **Confidence distribution** — most high-confidence predictions should
 *      actually be correct (rough calibration check).
 *
 * Costs real money: every case is a Gemini call. Keep the dataset small (~20
 * cases) for the fast-feedback CI loop; expand to 100+ for nightly runs.
 *
 * The thresholds and the dataset are identical to the Python and C# versions of
 * this exercise, on purpose — a cross-language debrief is only interesting if
 * everyone is measuring the same thing.
 */

// ---- thresholds (the spec's acceptance criteria turned into CE gates) -------

const ACCURACY_THRESHOLD = 0.85; // >= 85% of cases must be acceptable
const CATASTROPHIC_THRESHOLD = 0; // ZERO cases may hit an unacceptable category
const P95_LATENCY_SECONDS = 3.0; // generous; tighten once we have a baseline
const MIN_HIGH_CONF_ACCEPTABLE = 0.9; // of high-conf (>=0.8), at least 90% acceptable

interface EvalCase {
  description: string;
  amount: number;
  acceptable: string[];
  unacceptable: string[];
}

interface EvalResult {
  case: EvalCase;
  output: CategorisationOut | null;
  elapsed: number;
  error: string | null;
}

const DATASET_PATH = path.join(path.dirname(fileURLToPath(import.meta.url)), "eval_dataset.json");

// Explicit opt-in required. A missing key is a skip, not a failure — otherwise
// every developer without a key sees a red suite.
const hasKey = Boolean(process.env["GOOGLE_API_KEY"]);

describe.skipIf(!hasKey)("categorisation quality", () => {
  let results: EvalResult[] = [];

  const isAcceptable = (r: EvalResult) =>
    r.output !== null && r.case.acceptable.includes(r.output.category);
  const isCatastrophic = (r: EvalResult) =>
    r.output !== null && r.case.unacceptable.includes(r.output.category);

  /**
   * Run every case through the real categoriser, once, and cache the results.
   * This is the only expensive step — all four gates below read from it, so they
   * share a single full pass of the dataset.
   */
  beforeAll(async () => {
    const cases: EvalCase[] = JSON.parse(fs.readFileSync(DATASET_PATH, "utf8"));
    const client = new GeminiClient();

    for (const evalCase of cases) {
      const start = performance.now();
      try {
        const output = await categorise(evalCase.description, evalCase.amount, client);
        results.push({
          case: evalCase,
          output,
          elapsed: (performance.now() - start) / 1000,
          error: null,
        });
      } catch (err) {
        // Record and keep going — one failure shouldn't hide the rest.
        results.push({
          case: evalCase,
          output: null,
          elapsed: (performance.now() - start) / 1000,
          error: (err as Error).message,
        });
      }
    }
  });

  // ---- the gates -----------------------------------------------------------

  it("accuracy is above the threshold", () => {
    const acceptable = results.filter(isAcceptable).length;
    const accuracy = acceptable / results.length;

    const failures = results
      .filter((r) => !isAcceptable(r))
      .map(
        (r) =>
          `  - '${r.case.description}' -> ${r.output?.category ?? "ERROR"} ` +
          `(acceptable: ${r.case.acceptable.join(", ")})`,
      );

    expect(
      accuracy,
      `Accuracy ${(accuracy * 100).toFixed(1)}% below threshold ` +
        `${(ACCURACY_THRESHOLD * 100).toFixed(1)}%.\nFailing cases:\n${failures.join("\n")}`,
    ).toBeGreaterThanOrEqual(ACCURACY_THRESHOLD);
  });

  it("has zero catastrophic failures", () => {
    const catastrophics = results.filter(isCatastrophic);

    const detail = catastrophics
      .map(
        (r) =>
          `  - '${r.case.description}' -> ${r.output!.category} ` +
          `(explicitly unacceptable: ${r.case.unacceptable.join(", ")})`,
      )
      .join("\n");

    expect(
      catastrophics.length,
      `${catastrophics.length} catastrophic failure(s):\n${detail}`,
    ).toBeLessThanOrEqual(CATASTROPHIC_THRESHOLD);
  });

  it("p95 latency is below the ceiling", () => {
    const latencies = results.map((r) => r.elapsed).sort((a, b) => a - b);
    const p95 = latencies[Math.floor(latencies.length * 0.95)]!;
    const mean = latencies.reduce((a, b) => a + b, 0) / latencies.length;

    expect(
      p95,
      `p95 latency ${p95.toFixed(2)}s exceeds ceiling ${P95_LATENCY_SECONDS}s. ` +
        `mean=${mean.toFixed(2)}s median=${latencies[Math.floor(latencies.length / 2)]!.toFixed(2)}s ` +
        `max=${latencies.at(-1)!.toFixed(2)}s`,
    ).toBeLessThanOrEqual(P95_LATENCY_SECONDS);
  });

  it("high-confidence predictions are reliable", (ctx) => {
    const highConf = results.filter((r) => r.output !== null && r.output.confidence >= 0.8);
    if (highConf.length === 0) {
      ctx.skip("No high-confidence predictions in this run");
      return;
    }

    const rate = highConf.filter(isAcceptable).length / highConf.length;

    expect(
      rate,
      `High-confidence acceptance rate ${(rate * 100).toFixed(1)}% below threshold ` +
        `${(MIN_HIGH_CONF_ACCEPTABLE * 100).toFixed(1)}%. The model is overconfident.`,
    ).toBeGreaterThanOrEqual(MIN_HIGH_CONF_ACCEPTABLE);
  });

  /**
   * Not a gate — prints a summary so facilitators can eyeball what the model
   * actually did. Always passes.
   */
  it("prints the eval summary", () => {
    const total = results.length;
    const latencies = results.map((r) => r.elapsed).sort((a, b) => a - b);
    const acceptable = results.filter(isAcceptable).length;

    console.log("\n=== Eval summary ===");
    console.log(`  total cases:       ${total}`);
    console.log(`  acceptable:        ${acceptable} (${((acceptable / total) * 100).toFixed(1)}%)`);
    console.log(`  catastrophic:      ${results.filter(isCatastrophic).length}`);
    console.log(`  errors:            ${results.filter((r) => r.output === null).length}`);
    console.log(
      `  latency p50/p95:   ${latencies[Math.floor(latencies.length / 2)]!.toFixed(2)}s / ` +
        `${latencies[Math.floor(latencies.length * 0.95)]!.toFixed(2)}s`,
    );
    console.log();

    expect(total).toBeGreaterThan(0);
  });
});
