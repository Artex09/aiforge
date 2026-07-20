import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The build output (dist/) is served directly by the AIForge stdlib API server.
// In dev, /api is proxied to that same server so the SPA talks to a live engine.
export default defineConfig({
  plugins: [react()],
  base: "/",
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8787",
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    chunkSizeWarningLimit: 1200,
  },
});
