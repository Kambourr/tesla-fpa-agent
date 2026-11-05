import { describe, expect, it } from "vitest";
import schema from "./dashboard.schema.json";
import type { Dashboard } from "./types";

// A small valid dashboard. The type annotation makes TypeScript check every field.
const sample: Dashboard = {
  schema_version: 1,
  generated_at: "2026-11-05T08:00:00+00:00",
  latest_quarter: "2026-Q3",
  forward_forecast_published: false,
  last_full_run: null,
  run: {
    started_at: null,
    duration_seconds: null,
    stages: [{ name: "publish", seconds: null }],
    model: null,
    input_tokens: null,
    output_tokens: null,
    estimated_cost_usd: null,
    data_as_of: null,
  },
  quarters: [],
  qa: null,
  backtest: { rows: [], averages: { total_revenue: null } },
  scenario_flex: {
    deliveries_pct: { bull: 10, base: 0, bear: -10 },
    automotive_asp_pct: { bull: 5, base: 0, bear: -5 },
    gross_margin_bp: { bull: 100, base: 0, bear: -100 },
  },
  sources: {
    facts: 0,
    filings: 0,
    delivery_quarters: 0,
    earliest_filing_date: null,
    latest_filing_date: null,
  },
};

describe("dashboard.schema.json", () => {
  it("lists the same top-level keys as the Dashboard type", () => {
    expect([...schema.required].sort()).toEqual(Object.keys(sample).sort());
  });
});
