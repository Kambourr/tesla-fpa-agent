import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { makeTestDashboard } from "../data/testDashboard";
import type { BacktestRow, Dashboard, QuarterView } from "../data/types";
import { AccuracySection } from "./AccuracySection";

/** Invented backtest numbers for these tests only. */
const rows: BacktestRow[] = [
  { quarter: "2025-Q4", metric: "total_revenue", actual: 100, forecast: 82.9, abs_pct_error: 17.1 },
  { quarter: "2025-Q4", metric: "gross_profit", actual: 50, forecast: 40, abs_pct_error: 20 },
  { quarter: "2025-Q4", metric: "operating_income", actual: 10, forecast: 24.32, abs_pct_error: 143.2 },
  { quarter: "2025-Q3", metric: "total_revenue", actual: 90, forecast: null, abs_pct_error: null },
  { quarter: "2025-Q3", metric: "gross_profit", actual: 30, forecast: 33, abs_pct_error: 10 },
  { quarter: "2025-Q3", metric: "operating_income", actual: 20, forecast: 22, abs_pct_error: 5.5 },
];

function dashboardWith(backtestRows: BacktestRow[]): Dashboard {
  return {
    ...makeTestDashboard(),
    backtest: {
      rows: backtestRows,
      averages: { total_revenue: 12.3, gross_profit: 15.5, operating_income: 74.4 },
    },
  };
}

function selectedQuarter(id: string): QuarterView {
  return { ...makeTestDashboard().quarters[0], quarter: id };
}

function renderSection(backtestRows: BacktestRow[], selectedId: string) {
  return render(
    <AccuracySection
      dashboard={dashboardWith(backtestRows)}
      quarter={selectedQuarter(selectedId)}
      onSelectQuarter={() => {}}
    />,
  );
}

describe("AccuracySection", () => {
  test("renders rows oldest first, the averages, and a 143.2% error in full", () => {
    renderSection(rows, "2025-Q4");

    expect(screen.getByRole("heading", { level: 2, name: "Model accuracy" })).toBeTruthy();
    expect(
      screen.getByText(
        "Absolute percent error of the base forecast against first-reported actuals, for each published quarter. Large misses stay in the table.",
      ),
    ).toBeTruthy();

    const bodyRows = screen.getAllByRole("row").slice(1);
    expect(bodyRows.map((row) => within(row).getByRole("rowheader").textContent?.replace("Selected quarter", "").trim())).toEqual([
      "Q3 2025",
      "Q4 2025",
      "Average",
    ]);

    const q4 = bodyRows[1];
    expect(within(q4).getByText("17.1%")).toBeTruthy();
    expect(within(q4).getByText("20.0%")).toBeTruthy();
    expect(within(q4).getByText("143.2%")).toBeTruthy();

    const average = bodyRows[2];
    expect(within(average).getByText("12.3%")).toBeTruthy();
    expect(within(average).getByText("15.5%")).toBeTruthy();
    expect(within(average).getByText("74.4%")).toBeTruthy();
  });

  test("caps the bar at full width for an error over 100% and keeps the number", () => {
    renderSection(rows, "2025-Q4");
    const cell = screen.getByText("143.2%").closest("td") as HTMLElement;
    const fill = cell.querySelector(".acc-fill") as HTMLElement;
    expect(fill.style.width).toBe("100%");
    expect(cell.querySelector(".acc-over")?.textContent).toBe("+");
  });

  test("shows an em dash with 'not available' for a null error", () => {
    renderSection(rows, "2025-Q4");
    const q3 = screen.getAllByRole("row")[1];
    expect(within(q3).getByText("—")).toBeTruthy();
    expect(within(q3).getByText("not available")).toBeTruthy();
  });

  test("marks only the selected quarter's row", () => {
    renderSection(rows, "2025-Q3");
    const marked = screen.getByText("Selected quarter").closest("tr") as HTMLElement;
    expect(within(marked).getByRole("rowheader").textContent).toContain("Q3 2025");
    expect(marked.className).toBe("acc-selected");
    expect(screen.getAllByText("Selected quarter")).toHaveLength(1);
    expect(screen.getAllByRole("row").filter((row) => row.className === "acc-selected")).toHaveLength(1);
  });

  test("shows the empty state when there are no backtest rows", () => {
    renderSection([], "2025-Q4");
    expect(screen.getByText("No backtest yet: the model needs published quarters with forecasts.")).toBeTruthy();
    expect(screen.queryByRole("table")).toBeNull();
  });
});
