import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource/ibm-plex-sans/latin-400.css";
import "@fontsource/ibm-plex-sans/latin-500.css";
import "@fontsource/source-serif-4/latin-400.css";
import { App } from "./App";
// The published file is bundled into the build, so the page renders complete on
// first paint instead of inserting every section after a fetch (which shifted the
// layout by thousands of pixels). It is still the committed file the pipeline
// writes; the site redeploys whenever that file changes.
import published from "../public/data/dashboard.json";
import type { Dashboard } from "./data/types";
import "./styles/tokens.css";
import "./styles/global.css";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Missing #root");
}

createRoot(rootElement).render(
  <StrictMode>
    <App initialDashboard={published as unknown as Dashboard} />
  </StrictMode>,
);
