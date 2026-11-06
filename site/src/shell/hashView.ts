export const VIEW_IDS = [
  "overview",
  "bridge",
  "memo",
  "forecast",
  "accuracy",
  "ask",
  "method",
] as const;

export type ViewId = (typeof VIEW_IDS)[number];

export const VIEW_LABELS: Record<ViewId, string> = {
  overview: "Overview",
  bridge: "Revenue bridge",
  memo: "Analyst memo",
  forecast: "Forecast",
  accuracy: "Accuracy",
  ask: "Ask",
  method: "How it works",
};

export const VIEW_HASH: Record<ViewId, string> = {
  overview: "#/overview",
  bridge: "#/bridge",
  memo: "#/memo",
  forecast: "#/forecast",
  accuracy: "#/accuracy",
  ask: "#/ask",
  method: "#/method",
};

const PATH_VIEW: Record<string, ViewId> = {
  "": "overview",
  "/": "overview",
  "/overview": "overview",
  "/bridge": "bridge",
  "/memo": "memo",
  "/forecast": "forecast",
  "/accuracy": "accuracy",
  "/ask": "ask",
  "/method": "method",
};

/** In-page ids that used to open an M8 tab. */
const ANCHOR_VIEW: Record<string, ViewId> = {
  "method-title": "method",
  "analyst-memo-title": "memo",
  "forecast-heading": "forecast",
  "accuracy-heading": "accuracy",
  "ask-heading": "ask",
};

function rawHash(hash: string): string {
  const trimmed = hash.startsWith("#") ? hash.slice(1) : hash;
  try {
    return decodeURIComponent(trimmed);
  } catch {
    return trimmed;
  }
}

/**
 * Hash that should change the shell view. Empty, `#/`, and `#/overview` are
 * Overview. Old section ids map onto the matching view. Anything else (for
 * example `#about-title`) leaves the current view alone.
 */
export function viewFromHashChange(hash: string): ViewId | null {
  const raw = rawHash(hash);
  if (raw in PATH_VIEW) {
    return PATH_VIEW[raw];
  }
  const path = raw.split(/[?#]/)[0];
  if (path in PATH_VIEW) {
    return PATH_VIEW[path];
  }
  if (raw in ANCHOR_VIEW) {
    return ANCHOR_VIEW[raw];
  }
  return null;
}

export function initialView(hash: string): ViewId {
  return viewFromHashChange(hash) ?? "overview";
}

export function hashForView(view: ViewId): string {
  return VIEW_HASH[view];
}
