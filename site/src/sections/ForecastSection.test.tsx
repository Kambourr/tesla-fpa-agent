import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { Dashboard, Drivers, PnlLine, QuarterView } from "../data/types";
import { makeTestDashboard } from "../data/testDashboard";
import { ForecastSection } from "./ForecastSection";

const DRIVERS: Drivers = {
  deliveries: 500000.1234,
  automotive_asp: 40000.5555,
  gross_margin: 0.185,
  automotive_regulatory_credits: 100000000.1111,
  automotive_leasing: 300000000.0001,
  energy_generation_and_storage: 2000000000.5005,
  services_and_other: 4000000000.9999,
  operating_expenses: 4500000000.1234,
};

/* Invented actuals. Forecast and variance values come from the publish formulas. */
const LINES: PnlLine[] = [
  { metric: "deliveries", label: "Deliveries", unit: "units", forecast: 500000.1234, actual: 480000, variance: -20000.1234, variance_pct: -4, favorable: false },
  { metric: "automotive_asp", label: "Automotive ASP", unit: "USD_per_unit", forecast: 40000.5555, actual: 41000, variance: 999.4445, variance_pct: 2.4986, favorable: true },
  { metric: "automotive_sales", label: "Automotive sales", unit: "USD", forecast: 20000282686.0685, actual: 19680000000, variance: -320282686.0685, variance_pct: -1.6014, favorable: false },
  { metric: "automotive_regulatory_credits", label: "Regulatory credits", unit: "USD", forecast: 100000000.1111, actual: 113000000, variance: 12999999.8889, variance_pct: 13, favorable: true },
  { metric: "total_revenue", label: "Total revenue", unit: "USD", forecast: 26400282687.6801, actual: 25000000000, variance: -1400282687.6801, variance_pct: -5.304, favorable: false },
  { metric: "gross_margin", label: "Gross margin", unit: "percent", forecast: 18.5, actual: 19, variance: 0.5, variance_pct: 2.7027, favorable: true },
  { metric: "gross_profit", label: "Gross profit", unit: "USD", forecast: 4884052297.2208, actual: 4800000000, variance: -84052297.2208, variance_pct: -1.721, favorable: false },
  { metric: "operating_expenses", label: "Operating expenses", unit: "USD", forecast: 4500000000.1234, actual: 4400000000, variance: -100000000.1234, variance_pct: -2.2222, favorable: true },
  { metric: "operating_income", label: "Operating income", unit: "USD", forecast: 384052297.0974, actual: 300000000, variance: -84052297.0974, variance_pct: -21.8856, favorable: false },
];

const EMPTY_SCENARIOS = { bull: {}, base: {}, bear: {} };

const QUARTER: QuarterView = {
  quarter: "2026-Q3",
  label: "Q3 2026",
  kind: "backtest",
  has_forecast: true,
  filing: null,
  lines: LINES,
  drivers: DRIVERS,
  scenarios: EMPTY_SCENARIOS,
  bridges: { revenue: [], gross_profit: [], operating_income: [], free_cash_flow: [] },
  memo: null,
};

const NO_DRIVERS: QuarterView = {
  ...QUARTER,
  quarter: "2026-Q2",
  label: "Q2 2026",
  lines: [LINES[4]],
  drivers: null,
};

function dashboardWith(quarter: QuarterView): Dashboard {
  return { ...makeTestDashboard(), quarters: [quarter] };
}

function renderFor(quarter: QuarterView) {
  return render(
    <ForecastSection dashboard={dashboardWith(quarter)} quarter={quarter} onSelectQuarter={() => undefined} />,
  );
}

function rowFor(label: string): HTMLTableRowElement {
  const row = screen.getByRole("rowheader", { name: label }).closest("tr");
  if (row === null) {
    throw new Error(`No row for ${label}`);
  }
  return row;
}

function cellsFor(label: string): HTMLTableCellElement[] {
  return within(rowFor(label)).getAllByRole("cell") as HTMLTableCellElement[];
}

/* Plain assertions: the project has no jest-dom matchers. */
function expectText(element: Element, text: string) {
  expect(element.textContent).toContain(text);
}

function expectClass(element: Element, name: string) {
  expect(element.classList.contains(name)).toBe(true);
}

function expectNoClass(element: Element, name: string) {
  expect(element.classList.contains(name)).toBe(false);
}

describe("ForecastSection", () => {
  it("renders the heading, the ledger rule and one row per published line", () => {
    const { container } = renderFor(QUARTER);
    expect(screen.getByRole("heading", { level: 2, name: "Forecast and scenarios" })).toBeTruthy();
    expect(container.querySelector("hr.ledger")).not.toBeNull();
    for (const line of LINES) {
      expect(screen.getByRole("rowheader", { name: line.label })).toBeTruthy();
    }
    expect(screen.getAllByRole("columnheader").map((h) => h.textContent)).toEqual([
      "Line",
      "Forecast",
      "Actual",
      "Variance $",
      "Variance %",
    ]);
  });

  it("formats the base forecast and variance in the line's unit", () => {
    renderFor(QUARTER);
    expectText(cellsFor("Deliveries")[0], "500,000");
    expectText(cellsFor("Deliveries")[3], "−4.0%");
    expectText(cellsFor("Total revenue")[0], "$26.40B");
    expectText(cellsFor("Total revenue")[2], "−$1.40B");
    expectText(cellsFor("Gross margin")[0], "18.5%");
    expectText(cellsFor("Gross margin")[2], "+0.5 pts");
  });

  it("shows a favorable or unfavorable word for each variance cell, not color alone", () => {
    renderFor(QUARTER);
    const unfavorable = screen.getAllByText("unfavorable");
    const favorable = screen.getAllByText("favorable");
    expect(unfavorable.length).toBeGreaterThan(0);
    expect(favorable.length).toBeGreaterThan(0);
    for (const word of [...unfavorable, ...favorable]) {
      expectClass(word, "visually-hidden");
    }
    // Operating expenses are a cost line, so a variance below forecast is favorable.
    expectText(cellsFor("Operating expenses")[2], "−$100M");
    expectClass(cellsFor("Operating expenses")[2], "forecast-table__variance--favorable");
    expectText(cellsFor("Operating expenses")[2], "favorable");
    expectClass(cellsFor("Total revenue")[2], "forecast-table__variance--unfavorable");
    expectText(cellsFor("Total revenue")[2], "unfavorable");
  });

  it("starts on Base and switches the total revenue forecast when Bull is chosen", async () => {
    const user = userEvent.setup();
    renderFor(QUARTER);
    const bull = screen.getByRole("button", { name: "Bull" });
    const base = screen.getByRole("button", { name: "Base" });
    expect(base.getAttribute("aria-pressed")).toBe("true");
    expect(bull.getAttribute("aria-pressed")).toBe("false");
    expectText(cellsFor("Total revenue")[0], "$26.40B");

    await user.click(bull);
    expect(bull.getAttribute("aria-pressed")).toBe("true");
    expect(base.getAttribute("aria-pressed")).toBe("false");
    expectText(cellsFor("Total revenue")[0], "$29.50B");
    expectText(cellsFor("Gross margin")[0], "19.5%");
    expectText(cellsFor("Gross margin")[2], "−0.5 pts");
    expectText(cellsFor("Gross margin")[2], "unfavorable");
    expectClass(cellsFor("Total revenue")[0], "forecast-table__cell--moved");
    // Lines the flex does not move keep their published values and do not animate.
    expectText(cellsFor("Regulatory credits")[0], "$100M");
    expectNoClass(cellsFor("Regulatory credits")[0], "forecast-table__cell--moved");
  });

  it("gives the first column the sticky class inside a scrolling wrapper", () => {
    const { container } = renderFor(QUARTER);
    const wrap = container.querySelector(".forecast__table-wrap");
    expect(wrap).not.toBeNull();
    expectClass(screen.getByRole("columnheader", { name: "Line" }), "forecast-table__line");
    expectClass(screen.getByRole("rowheader", { name: "Deliveries" }), "forecast-table__line");
  });

  it("states the flexes from the published scenario_flex", () => {
    renderFor(QUARTER);
    expect(
      screen.getByText(
        "Bear and bull flex deliveries by ±10%, ASP by ±5%, and gross margin by ±100 basis points from the base forecast.",
      ),
    ).toBeTruthy();
  });

  it("disables Bull and Bear with a note when the quarter has no drivers", () => {
    renderFor(NO_DRIVERS);
    expect((screen.getByRole("button", { name: "Bull" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Bear" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByRole("button", { name: "Base" }).getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByText("Scenarios need a base forecast for this quarter.")).toBeTruthy();
  });
});
