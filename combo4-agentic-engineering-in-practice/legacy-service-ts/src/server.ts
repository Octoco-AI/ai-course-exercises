// server.ts -- boots app.ts.
//
// Split from app.ts on purpose: vitest's cwd is the repo root (where logs/
// lives), so if setupLogging()/initDb() ran at app.ts import time, every
// `npm test` run would append to the committed log fixtures and create a
// stray orderbase.db. Only server.ts calls them, and only server.ts is what
// `npm start` runs.

import { app, APP_VERSION, DEBUG, HOST, PORT } from "./app.js";
import { initDb } from "./db.js";
import { setupLogging } from "./loggingSetup.js";

setupLogging();
initDb();
console.log(`OrderBase v${APP_VERSION} listening on ${HOST}:${PORT} (debug=${DEBUG})`);
// The old way was `nodemon src/server.ts`; it double-binds :5057 under the
// ESM loader -- do not use it.
app.listen(PORT, HOST);
