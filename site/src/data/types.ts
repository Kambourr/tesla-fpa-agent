/**
 * Types for site/public/data/dashboard.json. Hand-written to match
 * agent/publish_schema.py field for field. dashboard.schema.json is generated
 * from those models, and types.test.ts checks the top-level keys against it.
 * Money is a JSON number in USD, rounded to four decimals, and null when missing.
 */

export type Unit = "USD" | "units" | "USD_per_unit" | "percent";
export type Scenario = "bull" | "base" | "bear";
export type StageName = "ingest" | "load" | "forecast" | "explain" | "verify" | "publish";
export type BridgeName = "revenue" | "gross_profit" | "operating_income" | "free_cash_flow";
export type ClaimStatus = "verified" | "flagged" | "unsupported";

export interface Stage {
  name: StageName;
  seconds: number | null;
}

export interface RunMetadata {
  started_at: string | null;
  duration_seconds: number | null;
  stages: Stage[];
  model: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  estimated_cost_usd: number | null;
  data_as_of: string | null;
}

export interface Filing {
  form: string;
  accession: string;
  /** YYYY-MM-DD */
  filing_date: string;
  url: string;
}

export interface PnlLine {
  metric: string;
  label: string;
  unit: Unit;
  forecast: number | null;
  actual: number | null;
  variance: number | null;
  variance_pct: number | null;
  /** Cost lines are favorable when the variance is below zero. Null when there is no variance or it is zero. */
  favorable: boolean | null;
}

/** Base forecast values the browser needs to recompute the scenarios. gross_margin is a fraction. */
export interface Drivers {
  deliveries: number | null;
  automotive_asp: number | null;
  gross_margin: number | null;
  automotive_regulatory_credits: number | null;
  automotive_leasing: number | null;
  energy_generation_and_storage: number | null;
  services_and_other: number | null;
  operating_expenses: number | null;
}

export interface BridgeBar {
  driver: string;
  label: string;
  value: number;
  favorable: boolean;
}

export interface VerificationCounts {
  verified: number;
  flagged: number;
  unsupported: number;
  total: number;
}

export interface ClaimView {
  metric: string;
  period: string;
  value: number;
  unit: string;
  sentence_ref: string;
  status: ClaimStatus;
  expected: number | null;
  expected_unit: string | null;
  source: string | null;
  source_url: string | null;
}

export interface Memo {
  text: string;
  claims: ClaimView[];
  verification: VerificationCounts;
}

export interface QuarterView {
  quarter: string;
  /** For example "Q3 2026". */
  label: string;
  kind: "backtest" | "forward";
  has_forecast: boolean;
  filing: Filing | null;
  lines: PnlLine[];
  drivers: Drivers | null;
  /** Metric to value. Gross margin is a fraction here, as stored. */
  scenarios: Record<Scenario, Record<string, number | null>>;
  bridges: Record<BridgeName, BridgeBar[]>;
  memo: Memo | null;
}

export interface QaAnswer {
  number: number;
  question: string;
  text: string;
  claims: ClaimView[];
}

export interface QaSet {
  quarter: string;
  answers: QaAnswer[];
  verification: VerificationCounts;
}

export interface BacktestRow {
  quarter: string;
  metric: string;
  actual: number | null;
  forecast: number | null;
  abs_pct_error: number | null;
}

export interface Backtest {
  rows: BacktestRow[];
  averages: Record<string, number | null>;
}

export interface ScenarioTriple {
  bull: number;
  base: number;
  bear: number;
}

export interface ScenarioFlex {
  deliveries_pct: ScenarioTriple;
  automotive_asp_pct: ScenarioTriple;
  gross_margin_bp: ScenarioTriple;
}

export interface Dashboard {
  schema_version: 1;
  generated_at: string;
  latest_quarter: string;
  forward_forecast_published: boolean;
  run: RunMetadata;
  /** Oldest first. */
  quarters: QuarterView[];
  qa: QaSet | null;
  backtest: Backtest;
  scenario_flex: ScenarioFlex;
}

/**
 * Fetches `${baseUrl}data/dashboard.json`. Throws on a non-2xx response.
 * The payload is not validated at runtime; the Python schema test is the lock.
 */
export async function loadDashboard(baseUrl: string): Promise<Dashboard> {
  const response = await fetch(`${baseUrl}data/dashboard.json`);
  if (!response.ok) {
    throw new Error(`dashboard.json request failed: ${response.status}`);
  }
  return (await response.json()) as Dashboard;
}
