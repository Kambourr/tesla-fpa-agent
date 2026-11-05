/**
 * Browser scenario math. A port of `_flex` in agent/scenarios.py and of the
 * variance and favorable rules in agent/publish.py.
 *
 * Python uses Decimal, so the port uses exact decimal arithmetic on BigInts.
 * Each published number is read through its shortest decimal string, which is
 * the four-place value the publisher wrote. Results are rounded to four places
 * at the end, half to even, the same as Decimal.quantize(0.0001) in Python.
 */
import type { Drivers, Scenario, ScenarioFlex } from "../data/types";

const PLACES = 4;

/** Metrics the bull and bear flexes move. Other lines keep their published forecast. */
export const SCENARIO_METRICS: readonly string[] = [
  "deliveries",
  "automotive_asp",
  "automotive_sales",
  "total_revenue",
  "gross_margin",
  "gross_profit",
  "operating_income",
];

/** For these lines a variance below zero is favorable. For every other line, above zero is. */
export const COST_LINES: ReadonlySet<string> = new Set([
  "research_and_development",
  "selling_general_and_administrative",
  "operating_expenses",
  "purchases_of_property_and_equipment",
]);

/** An exact decimal: value = n / 10^scale. */
interface Dec {
  n: bigint;
  scale: number;
}

function toDec(x: number): Dec {
  const match = /^(-?)(\d+)(?:\.(\d+))?(?:e([+-]?\d+))?$/i.exec(String(x));
  if (match === null) {
    throw new RangeError(`Not a finite number: ${x}`);
  }
  const [, sign, whole, fraction = "", exponent = "0"] = match;
  let digits = whole + fraction;
  let scale = fraction.length - Number(exponent);
  if (scale < 0) {
    digits += "0".repeat(-scale);
    scale = 0;
  }
  const n = BigInt(digits);
  return { n: sign === "-" ? -n : n, scale };
}

function align(a: Dec, b: Dec): [bigint, bigint, number] {
  const scale = Math.max(a.scale, b.scale);
  return [a.n * 10n ** BigInt(scale - a.scale), b.n * 10n ** BigInt(scale - b.scale), scale];
}

function add(a: Dec, b: Dec): Dec {
  const [x, y, scale] = align(a, b);
  return { n: x + y, scale };
}

function sub(a: Dec, b: Dec): Dec {
  const [x, y, scale] = align(a, b);
  return { n: x - y, scale };
}

function mul(a: Dec, b: Dec): Dec {
  return { n: a.n * b.n, scale: a.scale + b.scale };
}

/** Round num / den to the nearest integer, ties to even. den must be positive. */
function roundDivide(num: bigint, den: bigint): bigint {
  const negative = num < 0n;
  const magnitude = negative ? -num : num;
  let quotient = magnitude / den;
  const twiceRemainder = (magnitude % den) * 2n;
  if (twiceRemainder > den || (twiceRemainder === den && quotient % 2n === 1n)) {
    quotient += 1n;
  }
  return negative ? -quotient : quotient;
}

/** The value times 10^4, rounded half to even. */
function quantize(d: Dec): bigint {
  if (d.scale <= PLACES) {
    return d.n * 10n ** BigInt(PLACES - d.scale);
  }
  return roundDivide(d.n, 10n ** BigInt(d.scale - PLACES));
}

function scaledToNumber(scaled: bigint): number {
  const negative = scaled < 0n;
  const digits = (negative ? -scaled : scaled).toString().padStart(PLACES + 1, "0");
  const text = `${digits.slice(0, -PLACES)}.${digits.slice(-PLACES)}`;
  return Number(negative ? `-${text}` : text);
}

function quantizedScaled(x: number | null): bigint | null {
  return x === null ? null : quantize(toDec(x));
}

function quantizedNumber(d: Dec | null): number | null {
  return d === null ? null : scaledToNumber(quantize(d));
}

function exact(value: number | null): Dec | null {
  return value === null ? null : toDec(value);
}

/** value * (1 + pct / 100), exact. */
function flexPercent(value: number | null, pct: number): Dec | null {
  if (value === null) {
    return null;
  }
  const amount = toDec(pct);
  const factor = add({ n: 1n, scale: 0 }, { n: amount.n, scale: amount.scale + 2 });
  return mul(toDec(value), factor);
}

/** value + bp / 10000, exact. The result is a fraction. */
function flexBasisPoints(value: number | null, bp: number): Dec | null {
  if (value === null) {
    return null;
  }
  const amount = toDec(bp);
  return add(toDec(value), { n: amount.n, scale: amount.scale + 4 });
}

/**
 * Rebuild the flexed forecast lines from the base drivers for one scenario.
 * Returns the same metrics as the Python `_flex` output that the drivers cover.
 * A null driver makes every line that depends on it null, as in Python.
 */
export function recomputeScenario(
  drivers: Drivers,
  flex: ScenarioFlex,
  scenario: Scenario,
): Record<string, number | null> {
  const deliveries = flexPercent(drivers.deliveries, flex.deliveries_pct[scenario]);
  const asp = flexPercent(drivers.automotive_asp, flex.automotive_asp_pct[scenario]);
  const margin = flexBasisPoints(drivers.gross_margin, flex.gross_margin_bp[scenario]);
  const credits = exact(drivers.automotive_regulatory_credits);
  const leasing = exact(drivers.automotive_leasing);
  const energy = exact(drivers.energy_generation_and_storage);
  const services = exact(drivers.services_and_other);
  const opex = exact(drivers.operating_expenses);

  const sales = deliveries && asp ? mul(deliveries, asp) : null;
  const total =
    sales && credits && leasing && energy && services
      ? add(add(add(add(sales, credits), leasing), energy), services)
      : null;
  const profit = total && margin ? mul(total, margin) : null;
  const income = profit && opex ? sub(profit, opex) : null;

  return {
    deliveries: quantizedNumber(deliveries),
    automotive_asp: quantizedNumber(asp),
    automotive_sales: quantizedNumber(sales),
    total_revenue: quantizedNumber(total),
    gross_margin: quantizedNumber(margin),
    gross_profit: quantizedNumber(profit),
    operating_income: quantizedNumber(income),
    automotive_regulatory_credits: quantizedNumber(credits),
    automotive_leasing: quantizedNumber(leasing),
    energy_generation_and_storage: quantizedNumber(energy),
    services_and_other: quantizedNumber(services),
    operating_expenses: quantizedNumber(opex),
  };
}

/** A fraction times 100, as a percent line (19.6 for 0.196). Exact. */
export function percentOfFraction(fraction: number | null): number | null {
  if (fraction === null) {
    return null;
  }
  return quantizedNumber(mul(toDec(fraction), { n: 100n, scale: 0 }));
}

/** Actual minus forecast, both rounded to four places first, as publish does. */
export function varianceOf(actual: number | null, forecast: number | null): number | null {
  const a = quantizedScaled(actual);
  const f = quantizedScaled(forecast);
  if (a === null || f === null) {
    return null;
  }
  return scaledToNumber(a - f);
}

/** Variance over the absolute forecast, times 100, rounded to four places. Null when the forecast is zero. */
export function variancePercentOf(variance: number | null, forecast: number | null): number | null {
  const v = quantizedScaled(variance);
  const f = quantizedScaled(forecast);
  if (v === null || f === null || f === 0n) {
    return null;
  }
  const absForecast = f < 0n ? -f : f;
  return scaledToNumber(roundDivide(v * 1_000_000n, absForecast));
}

/** Null when there is no variance or it is zero. */
export function isFavorable(metric: string, variance: number | null): boolean | null {
  if (variance === null || variance === 0) {
    return null;
  }
  return COST_LINES.has(metric) ? variance < 0 : variance > 0;
}
