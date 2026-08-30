import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    // Tests run against src/starter by default; TINY_AGENT_IMPL=reference
    // switches them to the worked solution. See tests/impl.ts.
    include: ["tests/**/*.test.ts"],
    environment: "node",
  },
});
