/**
 * Formatting helpers for tick marks. Pure functions, no React.
 *
 * Two kinds of number reach these helpers:
 * - a claim value, written as it appears in the prose (28.05 with unit "USD billion"), and
 * - an expected value, stored in base units (28046000000 with expected_unit "USD").
 */

const MINUS = "−";

export type UnitKind = "usd" | "usd_per_unit" | "percent" | "units";

/** Maps a unit string (a fact unit such as "USD" or a claim unit such as "USD billion") to a kind. */
export function unitKind(unit: string): UnitKind {
  const u = unit.trim().toLowerCase();
  if (u === "usd_per_unit" || (u.includes("per") && (u.includes("usd") || u.includes("$")))) {
    return "usd_per_unit";
  }
  if (u.includes("percent") || u.includes("%") || u.includes("point") || u === "pct" || u === "pp") {
    return "percent";
  }
  if (u.includes("usd") || u.includes("$") || u.includes("dollar")) {
    return "usd";
  }
  return "units";
}

/** Inserts thousands separators into the integer part of a plain decimal string. */
function addCommas(plain: string): string {
  const [integer, fraction] = plain.split(".");
  const grouped = integer.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return fraction === undefined ? grouped : `${grouped}.${fraction}`;
}

/** A non-negative number as a plain decimal string with no exponent and no trailing zeros. */
function plainNumber(absolute: number): string {
  return String(Number(absolute.toPrecision(12)));
}

/**
 * Formats an expected value stored in base units, for the filing-shows line.
 * USD: $28.05B, $718M, $41,302 (per unit). Percent: 19.6%. Units: 486,532.
 */
export function formatExpected(value: number, unit: string | null): string {
  const kind = unitKind(unit ?? "units");
  const sign = value < 0 ? MINUS : "";
  const absolute = Math.abs(value);
  switch (kind) {
    case "usd": {
      if (absolute >= 999_500_000) return `${sign}$${(absolute / 1e9).toFixed(2)}B`;
      if (absolute >= 1e6) return `${sign}$${Math.round(absolute / 1e6)}M`;
      return `${sign}$${addCommas(String(Math.round(absolute)))}`;
    }
    case "usd_per_unit":
      return `${sign}$${addCommas(String(Math.round(absolute)))}`;
    case "percent":
      return `${sign}${absolute.toFixed(1)}%`;
    case "units":
      return `${sign}${addCommas(String(Math.round(absolute)))}`;
  }
}

/**
 * Formats a claim value the way it reads in the prose:
 * 28.05 "USD billion" becomes $28.05B, -7.48 "USD billion" becomes −$7.48B,
 * -21.1 "percent" becomes −21.1%, 486532 "units" becomes 486,532.
 */
export function formatClaimValue(value: number, unit: string): string {
  const kind = unitKind(unit);
  const u = unit.trim().toLowerCase();
  const sign = value < 0 ? MINUS : "";
  const plain = plainNumber(Math.abs(value));
  switch (kind) {
    case "usd": {
      let suffix = "";
      if (/billion|\bbn\b|\bb\b/.test(u)) suffix = "B";
      else if (/million|\bmm?\b/.test(u)) suffix = "M";
      else if (/thousand|\bk\b/.test(u)) suffix = "K";
      const digits = suffix ? plain : addCommas(plain);
      return `${sign}$${digits}${suffix}`;
    }
    case "usd_per_unit":
      return `${sign}$${addCommas(plain)}`;
    case "percent":
      return `${sign}${plain}%`;
    case "units":
      return `${sign}${addCommas(plain)}${u.includes("thousand") ? " thousand" : ""}`;
  }
}

const KNOWN_PARTS: Record<string, (rest: string[]) => string | null> = {
  actual: (rest) => `actual ${words(rest.join("."))}`,
  variance: (rest) => `Variance in ${words(rest.join("."))}`,
  variance_pct: (rest) => `Variance in ${words(rest.join("."))} (%)`,
  forecast: (rest) => (rest.length === 2 ? `${words(rest[0])} forecast: ${words(rest[1])}` : null),
  bridge: (rest) => (rest.length === 2 ? `${words(rest[0])} bridge: ${words(rest[1])}` : null),
  backtest: (rest) => {
    if (rest.length !== 2) return null;
    if (rest[1] === "abs_pct_error") return `Backtest error: ${words(rest[0])}`;
    if (rest[1] === "average_abs_pct_error") return `Backtest average error: ${words(rest[0])}`;
    return null;
  },
};

function words(text: string): string {
  return text.replace(/_/g, " ");
}

function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/**
 * The source line label for a metric key, in sentence case.
 * actual.total_revenue -> "Actual total revenue"; bridge.revenue.volume -> "Revenue bridge: volume".
 * Unknown keys fall back to the key with dots and underscores turned into spaces.
 */
export function metricLabel(metric: string): string {
  const [head, ...rest] = metric.split(".");
  const build = KNOWN_PARTS[head];
  const built = build ? build(rest) : null;
  return capitalize(built ?? words(metric.replace(/\./g, " ")));
}

/** "2026-Q3" becomes "Q3 2026"; "12Q" becomes "Last 12 quarters"; anything else is null. */
export function periodLabel(period: string): string | null {
  const quarter = /^(\d{4})-Q([1-4])$/.exec(period);
  if (quarter) return `Q${quarter[2]} ${quarter[1]}`;
  if (period === "12Q") return "Last 12 quarters";
  return null;
}
