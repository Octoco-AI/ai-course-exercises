import Fastify, { type FastifyInstance } from "fastify";

import { categorise, type LlmClient } from "./core.js";
import { CANONICAL_CATEGORIES, ContractViolationError, ExpenseIn } from "./models.js";

/**
 * Fastify app exposing the categoriser.
 *
 * Built as a factory taking the {@link LlmClient} so the API tests can inject a
 * fake and boot the real routes in-process — the TypeScript equivalent of
 * ASP.NET's WebApplicationFactory or FastAPI's TestClient with a dependency
 * override.
 */
export function buildApp(client: LlmClient, options: { logger?: boolean } = {}): FastifyInstance {
  const app = Fastify({ logger: options.logger ?? false });

  /** Liveness probe. */
  app.get("/health", async () => ({ status: "ok" }));

  /** The canonical category list. Useful for API consumers and tests. */
  app.get("/categories", async () => ({ categories: [...CANONICAL_CATEGORIES] }));

  /**
   * Categorise a single expense.
   *
   * Returns 502 if the LLM returns malformed output (contract violation). The
   * confidence-threshold fallback (returning "Other" with used_fallback=true)
   * is a SUCCESSFUL response, not an error — the client needs to know the model
   * wasn't confident, not that everything failed.
   */
  app.post("/categorise", async (request, reply) => {
    const parsed = ExpenseIn.safeParse(request.body);
    if (!parsed.success) {
      return reply.status(400).send({
        error: "invalid request",
        detail: parsed.error.issues.map((i) => `${i.path.join(".")}: ${i.message}`),
      });
    }

    const start = performance.now();

    try {
      const result = await categorise(parsed.data.description, parsed.data.amount, client);

      const elapsedMs = performance.now() - start;
      app.log.info(
        `categorised "${parsed.data.description}" -> ${result.category} ` +
          `(conf=${result.confidence.toFixed(2)}, fallback=${result.used_fallback}, ${elapsedMs.toFixed(0)}ms)`,
      );

      return reply.status(200).send(result);
    } catch (err) {
      if (err instanceof ContractViolationError) {
        // Worth logging loudly — this is the "model started misbehaving" signal
        // the CE pipeline watches for.
        app.log.warn(`Contract violation from LLM: ${err.message}`);
        return reply.status(502).send({
          error: "LLM returned unparseable output",
          detail: err.message,
        });
      }

      // Missing API key, etc. — configuration problem.
      return reply.status(500).send({ error: (err as Error).message });
    }
  });

  return app;
}
