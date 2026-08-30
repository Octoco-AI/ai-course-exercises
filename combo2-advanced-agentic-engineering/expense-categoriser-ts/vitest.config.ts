import { defineConfig } from "vitest/config";

/**
 * Two projects, so evals are opt-in.
 *
 * This is the TypeScript equivalent of pytest's `-m evals` marker and xUnit's
 * [Trait("Category","Evals")]: you do not want the eval suite running on every
 * local save. `npm test` runs unit + API only; `npm run test:evals` runs the
 * suite that costs money.
 */
export default defineConfig({
  test: {
    projects: [
      {
        test: {
          name: "unit",
          include: ["tests/**/*.test.ts"],
          exclude: ["tests/evals/**"],
          environment: "node",
        },
      },
      {
        test: {
          name: "evals",
          include: ["tests/evals/**/*.test.ts"],
          environment: "node",
          // 22 sequential Gemini calls; the default 5s timeout is nowhere near.
          testTimeout: 120_000,
          hookTimeout: 120_000,
        },
      },
    ],
  },
});
