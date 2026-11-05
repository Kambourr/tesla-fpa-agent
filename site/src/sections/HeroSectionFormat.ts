import type { QuarterView } from "../data/types";

/** Typographic minus sign (U+2212), as the site style requires. */
const MINUS = "−";

export type BridgeStep = {
  key: string;
  label: string;
  /** "total" for forecast and actual bars, "driver" for the bridge steps between them. */
  kind: "total" | "driver";
  /** Total amount for totals, signed change for drivers. */
  value: number;
  /** Running level before the bar. */
  start: number;
  /** Running level after the bar. */
  end: number;
  /** Null for totals. */
  favorable: boolean | null;
};

export type RevenueBridgeModel = {
  label: string;
  forecast: number;
  actual: number;
  variance: number;
  variancePct: number | null;
  /** Forecast total, the driver steps in published order, then the actual total. */
  steps: BridgeStep[];
};

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

/** Unsigned dollar amount: "$28.05B" or "$718M". */
export function formatUsd(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 9.995e8) {
    return `$${(abs / 1e9).toFixed(2)}B`;
  }
  if (abs >= 1e7) {
    return `$${(abs / 1e6).toFixed(0)}M`;
  }
  return `$${(abs / 1e6).toFixed(1)}M`;
}

/** Dollar amount with a true minus or a plus sign: "−$7.48B", "+$24M". */
export function formatSignedUsd(value: number): string {
  return `${value < 0 ? MINUS : "+"}${formatUsd(value)}`;
}

/** Percent with one decimal and a sign: "−21.1%". */
export function formatSignedPercent(value: number): string {
  const sign = value < 0 ? MINUS : "+";
  return `${sign}${Math.abs(value).toFixed(1)}%`;
}

/** Axis tick in billions: "$10B", "$2.5B". */
export function formatAxisUsd(value: number): string {
  if (value === 0) {
    return "$0";
  }
  return `$${Number((value / 1e9).toFixed(2))}B`;
}

/** The lede sentence, for example "Q3 2026: forecast $35.53B, actual $28.05B, −$7.48B (−21.1%)." */
export function formatBridgeLede(model: RevenueBridgeModel): string {
  const pct = model.variancePct === null ? "" : ` (${formatSignedPercent(model.variancePct)})`;
  return `${model.label}: forecast ${formatUsd(model.forecast)}, actual ${formatUsd(model.actual)}, ${formatSignedUsd(model.variance)}${pct}.`;
}

/**
 * Builds the forecast-to-actual waterfall from the quarter's revenue bridge and its
 * total_revenue line. Returns null when the bridge is empty or a needed value is missing.
 */
export function buildRevenueBridge(quarter: QuarterView): RevenueBridgeModel | null {
  const bars = quarter.bridges?.revenue ?? [];
  if (bars.length === 0 || !bars.every((bar) => isFiniteNumber(bar.value))) {
    return null;
  }
  const line = (quarter.lines ?? []).find((item) => item.metric === "total_revenue");
  if (!line || !isFiniteNumber(line.forecast) || !isFiniteNumber(line.actual)) {
    return null;
  }
  const forecast = line.forecast;
  const actual = line.actual;
  const variance = isFiniteNumber(line.variance) ? line.variance : actual - forecast;
  const variancePct = isFiniteNumber(line.variance_pct)
    ? line.variance_pct
    : forecast !== 0
      ? (variance / forecast) * 100
      : null;

  const steps: BridgeStep[] = [
    { key: "forecast", label: "Forecast revenue", kind: "total", value: forecast, start: 0, end: forecast, favorable: null },
  ];
  let running = forecast;
  bars.forEach((bar, index) => {
    const end = running + bar.value;
    steps.push({
      key: `driver-${index}`,
      label: bar.label,
      kind: "driver",
      value: bar.value,
      start: running,
      end,
      favorable: bar.favorable,
    });
    running = end;
  });
  steps.push({ key: "actual", label: "Actual revenue", kind: "total", value: actual, start: 0, end: actual, favorable: null });

  return { label: quarter.label, forecast, actual, variance, variancePct, steps };
}
