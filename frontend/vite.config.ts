import os from "node:os";
import path from "node:path";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Keep Vite's dependency pre-bundle cache OUT of this Dropbox-synced folder. Dropbox holds file
  // handles on node_modules/.vite while syncing, which intermittently locks the cache and breaks
  // `vite` / `vite build` with EBUSY on rmdir. An OS-temp cacheDir sidesteps the lock entirely.
  cacheDir: path.join(os.tmpdir(), "openfpa-vite-cache"),
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    css: false,
  },
});
