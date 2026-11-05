import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource/schibsted-grotesk/latin-400.css";
import "@fontsource/schibsted-grotesk/latin-500.css";
import "@fontsource/schibsted-grotesk/latin-700.css";
import "@fontsource/newsreader/latin-400.css";
// The same committed file the dashboard bundles, so every count here matches it.
import published from "../../public/data/dashboard.json";
import type { Dashboard } from "../data/types";
import "../styles/tokens.css";
import "../styles/global.css";
import { WriteupPage } from "./WriteupPage";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Missing #root");
}

createRoot(rootElement).render(
  <StrictMode>
    <WriteupPage dashboard={published as unknown as Dashboard} />
  </StrictMode>,
);
