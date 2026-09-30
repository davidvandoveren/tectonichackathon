import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
    target: ["es2020", "safari15", "chrome100", "firefox100", "edge100"],
  },
  server: {
    // Keep the browser's Host header so the backend's same-origin CSRF check (Origin == Host)
    // also passes in dev. The short string form would rewrite Host to localhost:8000.
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: false },
      "/health": { target: "http://localhost:8000", changeOrigin: false },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
    css: true,
  },
});
