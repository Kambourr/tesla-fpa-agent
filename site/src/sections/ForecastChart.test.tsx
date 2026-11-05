import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import type { Dashboard, PnlLine, QuarterView } from "../data/types";
import { ForecastChart } from "./ForecastChart";

function revenueLine(forecast: number | null, actual: number | null): PnlLine {
  return {
    metric: "total_revenue",
    label: "Total revenue",
    unit: "USD",
    forecast,
    actual,
    variance: forecast !== null && actual !== null ? actual - forecast : null,
    variance_pct: null,
    favorable: null,
  };
}

function backtestQuarter(id: string, label: string, forecast: number | null, actual: number | null): QuarterView {
  return {
    quarter: id,
    label,
    kind: "backtest",
    has_forecast: true,
    filing: null,
    lines: [revenueLine(forecast, actual)],
    drivers: null,
    scenarios: {},
    bridges: {},
    memo: null,
  } as unknown as QuarterView;
}

/** Invented three-quarter dashboard. Every number is made up for these tests. */
function threeQuarterDashboard(): Dashboard {
  return {
    schema_version: 1,
    generated_at: "2026-11-05T00:00:00Z",
    latest_quarter: "2024-Q3",
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
    quarters: [
      backtestQuarter("2024-Q1", "Q1 2024", 21.5e9, 20.25e9),
      backtestQuarter("2024-Q2", "Q2 2024", 22e9, 23.5e9),
      backtestQuarter("2024-Q3", "Q3 2024", 24.75e9, 25.1e9),
    ],
    qa: null,
    backtest: { rows: [], averages: {} },
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
  } as Dashboard;
}

function selectedView(dashboard: Dashboard, id: string): QuarterView {
  const found = dashboard.quarters.find((quarter) => quarter.quarter === id);
  if (!found) {
    throw new Error(`no quarter ${id}`);
  }
  return found;
}

describe("ForecastChart", () => {
  test("renders one point per series per quarter", () => {
    const dashboard = threeQuarterDashboard();
    const { container } = render(
      <ForecastChart dashboard={dashboard} quarter={selectedView(dashboard, "2024-Q2")} onSelectQuarter={vi.fn()} />,
    );

    const forecastPoints = container.querySelectorAll('[data-series="forecast"]');
    const actualPoints = container.querySelectorAll('[data-series="actual"]');
    expect(forecastPoints.length).toBe(3);
    expect(actualPoints.length).toBe(3);
    expect(Array.from(forecastPoints).map((point) => point.getAttribute("data-quarter"))).toEqual([
      "2024-Q1",
      "2024-Q2",
      "2024-Q3",
    ]);
    expect(container.querySelectorAll(".forecast-chart-grid").length).toBeGreaterThanOrEqual(3);
    expect(container.querySelectorAll(".forecast-chart-grid").length).toBeLessThanOrEqual(5);
  });

  test("skips a missing value instead of drawing a point for it", () => {
    const dashboard = threeQuarterDashboard();
    dashboard.quarters[1] = backtestQuarter("2024-Q2", "Q2 2024", 22e9, null);
    const { container } = render(
      <ForecastChart dashboard={dashboard} quarter={selectedView(dashboard, "2024-Q2")} onSelectQuarter={vi.fn()} />,
    );

    expect(container.querySelectorAll('[data-series="forecast"]').length).toBe(3);
    expect(container.querySelectorAll('[data-series="actual"]').length).toBe(2);
  });

  test("marks the selected quarter with a rule, a bold label and a Selected note", () => {
    const dashboard = threeQuarterDashboard();
    const { container } = render(
      <ForecastChart dashboard={dashboard} quarter={selectedView(dashboard, "2024-Q2")} onSelectQuarter={vi.fn()} />,
    );

    expect(container.querySelectorAll(".forecast-chart-selected").length).toBe(1);
    const selectedLabel = screen.getByText("Selected").closest("button");
    expect(selectedLabel).not.toBeNull();
    expect(selectedLabel?.getAttribute("aria-current")).toBe("true");
    expect(selectedLabel?.classList.contains("is-selected")).toBe(true);
    expect(selectedLabel?.textContent).toContain("Q2 24");
  });

  test("puts the same values in a visually hidden table", () => {
    const dashboard = threeQuarterDashboard();
    render(
      <ForecastChart dashboard={dashboard} quarter={selectedView(dashboard, "2024-Q2")} onSelectQuarter={vi.fn()} />,
    );

    const table = screen.getByRole("table");
    expect(table.classList.contains("visually-hidden")).toBe(true);
    const rows = within(table).getAllByRole("row");
    expect(rows.length).toBe(4);
    expect(within(table).getByRole("columnheader", { name: "Base forecast" })).toBeTruthy();
    expect(within(table).getByRole("columnheader", { name: "Actual" })).toBeTruthy();
    expect(within(table).getByRole("cell", { name: "$21.50B" })).toBeTruthy();
    expect(within(table).getByRole("cell", { name: "$20.25B" })).toBeTruthy();
    expect(within(table).getByRole("cell", { name: "$25.10B" })).toBeTruthy();
  });

  test("calls onSelectQuarter with the quarter id when its label is clicked", async () => {
    const user = userEvent.setup();
    const dashboard = threeQuarterDashboard();
    const onSelectQuarter = vi.fn();
    render(
      <ForecastChart dashboard={dashboard} quarter={selectedView(dashboard, "2024-Q2")} onSelectQuarter={onSelectQuarter} />,
    );

    await user.click(screen.getByRole("button", { name: "Q1 24" }));
    expect(onSelectQuarter).toHaveBeenCalledWith("2024-Q1");
  });
});
