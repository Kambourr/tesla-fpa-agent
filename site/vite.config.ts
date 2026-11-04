import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// GitHub Pages project path for this repository. Publishing stays off until Jacob says otherwise.
export default defineConfig({
  base: "/tesla-fpa-agent/",
  plugins: [react()],
});
