import type { RunMetadata, StageName } from "../data/types";

/** The six pipeline stages in the order the agent runs them. */
export const STAGE_ORDER: StageName[] = ["ingest", "load", "forecast", "explain", "verify", "publish"];

export const STAGE_LABEL: Record<StageName, string> = {
  ingest: "Ingest",
  load: "Load",
  forecast: "Forecast",
  explain: "Explain",
  verify: "Verify",
  publish: "Publish",
};

/** Explain is the one AI step. The others run as code. */
export function stageKind(name: StageName): "Model" | "Code" {
  return name === "explain" ? "Model" : "Code";
}

const DATE_FORMAT = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});

/** "Nov 5, 2026". Timestamps are UTC, so the date is read in UTC for every viewer. */
export function formatRunDate(value: string | null): string | null {
  if (value === null) {
    return null;
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return DATE_FORMAT.format(parsed);
}

/** "4 s", "1.2 s", "38 s". Null stays null so the caller can show a dash. */
export function formatStageSeconds(seconds: number | null): string | null {
  if (seconds === null) {
    return null;
  }
  if (seconds < 0.1) {
    return "under 0.1 s";
  }
  if (seconds >= 10) {
    return `${Math.round(seconds)} s`;
  }
  return `${Math.round(seconds * 10) / 10} s`;
}

/** "47 seconds", "2 min 5 s", "2 min". */
export function formatRunTime(seconds: number | null): string | null {
  if (seconds === null) {
    return null;
  }
  if (seconds < 1) {
    return "under 1 second";
  }
  const total = Math.round(seconds);
  if (total < 60) {
    return `${total} ${total === 1 ? "second" : "seconds"}`;
  }
  const minutes = Math.floor(total / 60);
  const rest = total % 60;
  return rest === 0 ? `${minutes} min` : `${minutes} min ${rest} s`;
}

/** "$0.06", two decimals. Under a cent shows "<$0.01". */
export function formatCost(usd: number | null): string | null {
  if (usd === null) {
    return null;
  }
  if (usd < 0.01) {
    return "<$0.01";
  }
  return `$${usd.toFixed(2)}`;
}

/**
 * True until a full pipeline run has been recorded. Only a full run records the
 * model it narrated with. A publish-only run records its own start time and
 * duration, which must not read as the whole pipeline's run.
 */
export function isRunUnrecorded(run: RunMetadata): boolean {
  return run.model === null;
}
