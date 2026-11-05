import type { QuarterView, Scenario, ScenarioFlex, Unit } from "../data/types";
import {
  isFavorable,
  percentOfFraction,
  recomputeScenario,
  SCENARIO_METRICS,
  varianceOf,
  variancePercentOf,
} from "./scenarioMath";

const MINUS = "−";
const EM_DASH = "—";

export interface ForecastRow {
  metric: string;
  label: string;
  unit: Unit;
  forecast: number | null;
  actual: number | null;
  variance: number | null;
  variancePct: number | null;
  favorable: boolean | null;
  /** True when a bull or bear flex changed this row's forecast. */
  moved: boolean;
}

/**
 * The table rows for one scenario. Base shows the published forecast. Bull and
 * bear recompute the flexed metrics from the drivers and rebuild their variances
 * against the actual, with the publish rules.
 */
export function buildForecastRows(
  quarter: QuarterView,
  flex: ScenarioFlex,
  scenario: Scenario,
): ForecastRow[] {
  const recomputed =
    scenario !== "base" && quarter.drivers !== null
      ? recomputeScenario(quarter.drivers, flex, scenario)
      : null;

  return quarter.lines.map((line) => {
    const published: ForecastRow = {
      metric: line.metric,
      label: line.label,
      unit: line.unit,
      forecast: line.forecast,
      actual: line.actual,
      variance: line.variance,
      variancePct: line.variance_pct,
      favorable: line.favorable,
      moved: false,
    };
    if (recomputed === null || !SCENARIO_METRICS.includes(line.metric)) {
      return published;
    }
    const value = recomputed[line.metric] ?? null;
    const forecast = line.metric === "gross_margin" ? percentOfFraction(value) : value;
    const variance = varianceOf(line.actual, forecast);
    return {
      ...published,
      forecast,
      variance,
      variancePct: variancePercentOf(variance, forecast),
      favorable: isFavorable(line.metric, variance),
      moved: forecast !== line.forecast,
    };
  });
}

/** Thousands separators on a string of digits. */
function group(digits: string): string {
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/** A magnitude with no sign: $28.05B, $718M, $41,302, 486,532 or 19.6%. */
function magnitude(abs: number, unit: Unit): string {
  if (unit === "percent") {
    return `${abs.toFixed(1)}%`;
  }
  if (unit === "units") {
    return group(String(Math.round(abs)));
  }
  if (unit === "USD_per_unit") {
    return `$${group(String(Math.round(abs)))}`;
  }
  if (abs >= 999.5e6) {
    return `$${(abs / 1e9).toFixed(2)}B`;
  }
  if (abs >= 1e6) {
    return `$${Math.round(abs / 1e6)}M`;
  }
  return `$${group(String(Math.round(abs)))}`;
}

/** A forecast or actual value. Null shows an em dash. */
export function formatAmount(value: number | null, unit: Unit): string {
  if (value === null) {
    return EM_DASH;
  }
  const sign = value < 0 ? MINUS : "";
  return sign + magnitude(Math.abs(value), unit);
}

/** A variance in the line's unit, signed with a true minus. Percent lines show points. */
export function formatVariance(value: number | null, unit: Unit): string {
  if (value === null) {
    return EM_DASH;
  }
  const sign = value > 0 ? "+" : value < 0 ? MINUS : "";
  const abs = Math.abs(value);
  if (unit === "percent") {
    return `${sign}${abs.toFixed(1)} pts`;
  }
  return sign + magnitude(abs, unit);
}

/** A variance over the absolute forecast, as a signed percent. */
export function formatVariancePercent(value: number | null): string {
  if (value === null) {
    return EM_DASH;
  }
  const sign = value > 0 ? "+" : value < 0 ? MINUS : "";
  return `${sign}${Math.abs(value).toFixed(1)}%`;
}

/** The hidden word read after a variance: favorable, unfavorable, or unchanged. */
export function varianceWord(favorable: boolean | null, variance: number | null): string | null {
  if (favorable === true) {
    return "favorable";
  }
  if (favorable === false) {
    return "unfavorable";
  }
  return variance === 0 ? "unchanged" : null;
}

function signed(value: number): string {
  return `${value > 0 ? "+" : value < 0 ? MINUS : ""}${Math.abs(value)}`;
}

/** One sentence on the flexes, built from the published scenario_flex. */
export function flexSentence(flex: ScenarioFlex): string {
  const { deliveries_pct: d, automotive_asp_pct: a, gross_margin_bp: g } = flex;
  const mirrored = [d, a, g].every((triple) => triple.bull === -triple.bear);
  if (mirrored) {
    return `Bear and bull flex deliveries by ±${Math.abs(d.bull)}%, ASP by ±${Math.abs(a.bull)}%, and gross margin by ±${Math.abs(g.bull)} basis points from the base forecast.`;
  }
  return `Bull flexes deliveries by ${signed(d.bull)}%, ASP by ${signed(a.bull)}%, and gross margin by ${signed(g.bull)} basis points from the base forecast. Bear flexes deliveries by ${signed(d.bear)}%, ASP by ${signed(a.bear)}%, and gross margin by ${signed(g.bear)} basis points.`;
}
