/**
 * The verifier's rules from agent/verifier.py, in TypeScript, so a visitor can
 * change a figure and watch code check it. Same unit tables, same tolerances,
 * same sign rule, exact decimal arithmetic. parity.json (written by
 * tests/test_verifier_parity.py from the Python verifier) keeps the two equal.
 */

export type CheckStatus = "verified" | "flagged";

export interface CheckResult {
  status: CheckStatus;
  /** Plain-language reason, for the reader. */
  reason: string;
  /** The written value converted to the fact's unit, when the unit is compatible. */
  normalized: number | null;
}

const USD_MULTIPLIERS: Record<string, bigint> = {
  usd: 1n,
  dollars: 1n,
  "usd thousand": 1_000n,
  thousand: 1_000n,
  k: 1_000n,
  "usd million": 1_000_000n,
  million: 1_000_000n,
  m: 1_000_000n,
  mm: 1_000_000n,
  "usd billion": 1_000_000_000n,
  billion: 1_000_000_000n,
  b: 1_000_000_000n,
  bn: 1_000_000_000n,
};
const PERCENT_MULTIPLIERS: Record<string, bigint> = {
  percent: 1n,
  "%": 1n,
  pct: 1n,
  "percentage points": 1n,
  pp: 1n,
  points: 1n,
};
const UNIT_MULTIPLIERS: Record<string, bigint> = {
  units: 1n,
  vehicles: 1n,
  deliveries: 1n,
  cars: 1n,
  "thousand vehicles": 1_000n,
  "thousand units": 1_000n,
};
const USD_PER_UNIT_MULTIPLIERS: Record<string, bigint> = {
  "usd per vehicle": 1n,
  "usd per unit": 1n,
  usd_per_unit: 1n,
  "usd thousand per vehicle": 1_000n,
};
const TABLES: Record<string, Record<string, bigint>> = {
  USD: USD_MULTIPLIERS,
  percent: PERCENT_MULTIPLIERS,
  units: UNIT_MULTIPLIERS,
  USD_per_unit: USD_PER_UNIT_MULTIPLIERS,
};

/** An exact decimal: n × 10^-s. */
interface Dec {
  n: bigint;
  s: number;
}

export function parseDecimal(text: string): Dec | null {
  const match = /^([+-]?)(\d*)(?:\.(\d*))?(?:e([+-]?\d+))?$/i.exec(text.trim());
  if (!match || (match[2] === "" && (match[3] ?? "") === "")) {
    return null;
  }
  const [, sign, whole, fraction = "", exp = "0"] = match;
  let n = BigInt((whole || "0") + fraction);
  let s = fraction.length - Number(exp);
  if (s < 0) {
    n *= 10n ** BigInt(-s);
    s = 0;
  }
  return { n: sign === "-" ? -n : n, s };
}

function fromNumber(value: number): Dec | null {
  return Number.isFinite(value) ? parseDecimal(String(value)) : null;
}

function align(a: Dec, b: Dec): [bigint, bigint, number] {
  const s = Math.max(a.s, b.s);
  return [a.n * 10n ** BigInt(s - a.s), b.n * 10n ** BigInt(s - b.s), s];
}

function cmp(a: Dec, b: Dec): number {
  const [x, y] = align(a, b);
  return x === y ? 0 : x < y ? -1 : 1;
}

function sub(a: Dec, b: Dec): Dec {
  const [x, y, s] = align(a, b);
  return { n: x - y, s };
}

function abs(a: Dec): Dec {
  return { n: a.n < 0n ? -a.n : a.n, s: a.s };
}

function mul(a: Dec, b: Dec): Dec {
  return { n: a.n * b.n, s: a.s + b.s };
}

function toNumber(a: Dec): number {
  return Number(a.n) / 10 ** a.s;
}

const ZERO: Dec = { n: 0n, s: 0 };
const CURRENCY_TOLERANCE: Dec = { n: 5n, s: 3 };
const PERCENT_TOLERANCE: Dec = { n: 1n, s: 1 };

export function canonicalUnit(unit: string): string {
  return unit.trim().toLowerCase().replaceAll("$", " usd ").split(/\s+/).filter(Boolean).join(" ");
}

/** Round a / q to an integer, ties away from zero (Python's ROUND_HALF_UP). */
function roundHalfUp(a: Dec, q: Dec): bigint {
  const num = a.n * 10n ** BigInt(q.s);
  const den = q.n * 10n ** BigInt(a.s);
  const negative = num < 0n !== den < 0n;
  const absNum = num < 0n ? -num : num;
  const absDen = den < 0n ? -den : den;
  let quotient = absNum / absDen;
  if ((absNum % absDen) * 2n >= absDen) {
    quotient += 1n;
  }
  return negative ? -quotient : quotient;
}

/**
 * Check a written figure against the fact it cites. `valueText` is the figure
 * as written (its decimals set the precision for counts in thousands).
 * `expected` and `expectedUnit` are the fact sheet's value and unit, as
 * published in dashboard.json for each claim.
 */
export function checkFigure(
  valueText: string,
  unit: string,
  expected: number,
  expectedUnit: string,
): CheckResult {
  // The text as written: "134.8" and "135.0" carry different precision.
  const written = parseDecimal(valueText);
  const fact = fromNumber(expected);
  const table = TABLES[expectedUnit];
  if (written === null || fact === null) {
    return { status: "flagged", reason: "That is not a number.", normalized: null };
  }
  const multiplier = table?.[canonicalUnit(unit)];
  if (multiplier === undefined) {
    return {
      status: "flagged",
      reason: `The unit "${unit}" cannot be compared with the filing's unit.`,
      normalized: null,
    };
  }
  const normalized = mul(written, { n: multiplier, s: 0 });
  const normalizedNumber = toNumber(normalized);
  if (normalized.n !== 0n && fact.n !== 0n && normalized.n < 0n !== fact.n < 0n) {
    return {
      status: "flagged",
      reason: "The sign is wrong: a shortfall written as a gain, or the reverse.",
      normalized: normalizedNumber,
    };
  }

  if (expectedUnit === "USD" || expectedUnit === "USD_per_unit") {
    if (fact.n === 0n) {
      const ok = cmp(normalized, ZERO) === 0;
      return { status: ok ? "verified" : "flagged", reason: "Must be exactly zero.", normalized: normalizedNumber };
    }
    const allowed = mul(abs(fact), CURRENCY_TOLERANCE);
    const ok = cmp(abs(sub(normalized, fact)), allowed) <= 0;
    return {
      status: ok ? "verified" : "flagged",
      reason: ok ? "Within 0.5% of the filing." : "More than 0.5% away from the filing.",
      normalized: normalizedNumber,
    };
  }
  if (expectedUnit === "percent") {
    const ok = cmp(abs(sub(normalized, fact)), PERCENT_TOLERANCE) <= 0;
    return {
      status: ok ? "verified" : "flagged",
      reason: ok ? "Within 0.1 percentage points." : "More than 0.1 percentage points away.",
      normalized: normalizedNumber,
    };
  }
  // units: exact, except a figure written in thousands is rounded at the precision written.
  const unitMultiplier = UNIT_MULTIPLIERS[canonicalUnit(unit)] ?? 1n;
  if (unitMultiplier === 1n) {
    const ok = cmp(normalized, fact) === 0;
    return {
      status: ok ? "verified" : "flagged",
      reason: ok ? "Exact match." : "Vehicle counts must match exactly.",
      normalized: normalizedNumber,
    };
  }
  const quantum: Dec =
    written.s > 0 ? { n: unitMultiplier, s: written.s } : { n: unitMultiplier, s: 0 };
  const rounded = mul({ n: roundHalfUp(fact, quantum), s: 0 }, quantum);
  const ok = cmp(normalized, rounded) === 0;
  return {
    status: ok ? "verified" : "flagged",
    reason: ok
      ? "Matches the filing at the precision written."
      : "Does not match the filing at the precision written.",
    normalized: normalizedNumber,
  };
}
