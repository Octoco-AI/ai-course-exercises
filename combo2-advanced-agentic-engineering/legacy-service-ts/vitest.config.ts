import { defineConfig } from "vitest/config";

// Single project -- no evals here, no LLM calls in this artifact.
export default defineConfig({
  test: {
    include: ["tests/**/*.test.ts"],
    environment: "node",
  },
});
