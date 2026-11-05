import { resolve } from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// GitHub Pages project path for this repository.
export default defineConfig({
  base: "/tesla-fpa-agent/",
  plugins: [react()],
  // Emit bundled JSON as JSON.parse("...") rather than an object literal: faster to parse.
  json: { stringify: true },
  build: {
    rollupOptions: {
      // Two pages: the dashboard and the plain-language write-up.
      input: {
        main: resolve(__dirname, "index.html"),
        writeup: resolve(__dirname, "how-it-was-built.html"),
      },
    },
  },
});
