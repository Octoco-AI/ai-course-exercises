/**
 * Run locally:
 *     npm run dev
 *
 * Test:
 *     curl -X POST http://localhost:5080/categorise \
 *          -H "Content-Type: application/json" \
 *          -d '{"description": "Whole Foods", "amount": 45.23}'
 */
import "dotenv/config";

import { buildApp } from "./app.js";
import { GeminiClient } from "./geminiClient.js";

const app = buildApp(new GeminiClient(), { logger: true });

const host = process.env["HOST"] ?? "127.0.0.1";
const port = Number.parseInt(process.env["PORT"] ?? "5080", 10);

await app.listen({ host, port });
