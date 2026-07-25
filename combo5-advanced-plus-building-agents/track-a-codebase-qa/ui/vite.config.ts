import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // Dev server runs on :5173; proxy /api requests to the FastAPI backend
    // running on :8000. Means npm run dev works without CORS faff.
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    // Bundle everything into a single JS file for the backend to serve.
    // Small project; no code-splitting needed.
    target: "es2022",
  },
});
