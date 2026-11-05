import type { Dashboard } from "./data/types";

/** One picker row, derived from the published dashboard.json. */
export type QuarterRecord = {
  id: string;
  label: string;
  /** False when the quarter has fewer than four earlier quarters of history. */
  hasForecast: boolean;
};

export const needsHistoryMessage =
  "No forecast for this quarter: it needs four earlier quarters of history.";

/** Published backtest quarters, oldest first. A forward quarter is never in the picker. */
export function quarterRecords(dashboard: Dashboard): QuarterRecord[] {
  return dashboard.quarters
    .filter((quarter) => quarter.kind === "backtest")
    .map((quarter) => ({
      id: quarter.quarter,
      label: quarter.label,
      hasForecast: quarter.has_forecast,
    }));
}

export function latestQuarter(quarters: readonly QuarterRecord[]): QuarterRecord | undefined {
  return quarters[quarters.length - 1];
}
