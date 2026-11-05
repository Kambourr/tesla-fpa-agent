import type { BacktestRow } from "../data/types";

/** The three metrics the backtest table shows, in column order. */
export const accuracyMetrics = [
  { key: "total_revenue", label: "Revenue" },
  { key: "gross_profit", label: "Gross profit" },
  { key: "operating_income", label: "Operating income" },
] as const;

/** "2023-Q4" becomes "Q4 2023". Any other id is shown as it is. */
export function quarterLabel(id: string): string {
  const match = /^(\d{4})-Q([1-4])$/.exec(id);
  return match ? `Q${match[2]} ${match[1]}` : id;
}

/** abs_pct_error is already in percent units: 17.0519 means 17.1%. */
export function formatErrorPercent(value: number | null | undefined): string | null {
  if (value === null || value === undefined || !Number.isFinite(value)) return null;
  return `${value.toFixed(1)}%`;
}

/** Bar fill as a percent of the track. Capped at 100 so large misses do not overflow. */
export function barFillPercent(value: number): number {
  return Math.min(Math.max(value, 0), 100);
}

/** Quarter ids, oldest first. Ids are "YYYY-Qn", so string order is time order. */
export function backtestQuarters(rows: BacktestRow[]): string[] {
  return [...new Set(rows.map((row) => row.quarter))].sort();
}
