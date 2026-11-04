/**
 * Stand-in quarters until the pipeline publishes site/public/data.
 * Labels only. No dollar amounts. M4-T1 replaces this fixture.
 */
export type QuarterRecord = {
  id: string;
  label: string;
  /** False when the quarter has fewer than four earlier quarters of history. */
  hasForecast: boolean;
};

export const needsHistoryMessage =
  "No forecast for this quarter: it needs four earlier quarters of history.";

export const quarterFixture: readonly QuarterRecord[] = [
  { id: "2025-Q4", label: "Q4 2025", hasForecast: false },
  { id: "2026-Q1", label: "Q1 2026", hasForecast: true },
  { id: "2026-Q2", label: "Q2 2026", hasForecast: true },
  { id: "2026-Q3", label: "Q3 2026", hasForecast: true },
];

export function latestQuarter(quarters: readonly QuarterRecord[]): QuarterRecord | undefined {
  return quarters[quarters.length - 1];
}
