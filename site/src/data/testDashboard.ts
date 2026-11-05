/**
 * A tiny dashboard for component tests ONLY. Every number here is invented and
 * round. Never import this from production code: the page shows only
 * site/public/data/dashboard.json, which the pipeline writes from filings.
 */
import type { Dashboard, QuarterView } from "./types";

function quarter(id: string, label: string, hasForecast: boolean): QuarterView {
  return {
    quarter: id,
    label,
    kind: "backtest",
    has_forecast: hasForecast,
    filing: hasForecast
      ? {
          form: "10-Q",
          accession: "0000000000-00-000001",
          filing_date: "2026-10-22",
          url: "https://example.com/filing",
        }
      : null,
    lines: hasForecast
      ? [
          {
            metric: "total_revenue",
            label: "Total revenue",
            unit: "USD",
            forecast: 1000,
            actual: 900,
            variance: -100,
            variance_pct: -10,
            favorable: false,
          },
        ]
      : [],
    drivers: null,
    scenarios: {},
    bridges: hasForecast
      ? {
          revenue: [
            { driver: "volume", label: "Volume", value: -120, favorable: false },
            { driver: "price_mix", label: "Price and mix", value: 20, favorable: true },
          ],
        }
      : {},
    memo: null,
  } as QuarterView;
}

export function makeTestDashboard(): Dashboard {
  return {
    schema_version: 1,
    generated_at: "2026-11-05T00:00:00Z",
    latest_quarter: "2026-Q3",
    forward_forecast_published: false,
    last_full_run: null,
    first_drafts: { narratives: 0, recorded: 0, checked: 0, caught: 0, guard_hits: 0, rejected: 0, final_problems: 0, catches: [], first_issues: [], final_issues: [] },
    run: {
      started_at: null,
      duration_seconds: null,
      stages: [],
      model: null,
      input_tokens: null,
      output_tokens: null,
      estimated_cost_usd: null,
      data_as_of: null,
    },
    quarters: [quarter("2025-Q4", "Q4 2025", false), quarter("2026-Q3", "Q3 2026", true)],
    qa: null,
    backtest: { rows: [], averages: {} },
    scenario_flex: {
      deliveries_pct: { bull: 10, base: 0, bear: -10 },
      automotive_asp_pct: { bull: 5, base: 0, bear: -5 },
      gross_margin_bp: { bull: 100, base: 0, bear: -100 },
    },
    sources: {
      facts: 100,
      filings: 10,
      delivery_quarters: 8,
      earliest_filing_date: "2024-01-01",
      latest_filing_date: "2026-10-22",
    },
  } as Dashboard;
}
