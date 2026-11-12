import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "../App";
import type { Dashboard, QuarterView } from "../data/types";
import { makeTestDashboard } from "../data/testDashboard";
import { viewFromHashChange } from "../shell/hashView";
import { builtFrom, forwardQuarter, OutlookSection, outlookRows } from "./OutlookSection";

function withForward(dashboard: Dashboard): { dashboard: Dashboard; forward: QuarterView } {
  const latest = dashboard.quarters[dashboard.quarters.length - 1];
  const forward: QuarterView = {
    ...latest,
    quarter: "2026-Q4",
    label: "Q4 2026",
    kind: "forward",
    filing: null,
    memo: null,
    bridges: { revenue: [], gross_profit: [], operating_income: [], free_cash_flow: [] },
    lines: latest.lines.map((line) => ({
      ...line,
      actual: null,
      variance: null,
      variance_pct: null,
      favorable: null,
    })),
  };
  return {
    dashboard: { ...dashboard, quarters: [...dashboard.quarters, forward], forward_forecast_published: true },
    forward,
  };
}

describe("OutlookSection", () => {
  it("finds the forward quarter only when one is published", () => {
    const base = makeTestDashboard();
    expect(forwardQuarter(base)).toBeNull();
    expect(forwardQuarter(withForward(base).dashboard)?.quarter).toBe("2026-Q4");
  });

  it("shows bear, base, and bull columns for the key lines", () => {
    const { dashboard, forward } = withForward(makeTestDashboard());
    const rows = outlookRows(dashboard, forward);
    expect(rows.length).toBeGreaterThan(0);
    render(<OutlookSection dashboard={dashboard} quarter={forward} />);
    const headers = screen.getAllByRole("columnheader").map((cell) => cell.textContent);
    expect(headers).toEqual(["Line", "Bear", "Base", "Bull"]);
    expect(screen.getByRole("heading", { level: 2 }).textContent).toBe("Q4 2026: what the model expects");
  });

  it("labels it as a model forecast and says what is missing and why", () => {
    const { dashboard, forward } = withForward(makeTestDashboard());
    render(<OutlookSection dashboard={dashboard} quarter={forward} />);
    expect(screen.getByText("Model forecast · not yet reported")).toBeTruthy();
    expect(screen.getByText(/no actual, no variance bridge, and no memo/)).toBeTruthy();
    expect(screen.getByText(/not Tesla guidance, a consensus estimate, or investment advice/)).toBeTruthy();
  });

  it("names the latest filing it is built from", () => {
    const { dashboard } = withForward(makeTestDashboard());
    const source = builtFrom(dashboard);
    if (source) {
      expect(source.form).toMatch(/10-[QK]/);
    }
  });
});

describe("outlook view in the shell", () => {
  it("routes #/outlook", () => {
    expect(viewFromHashChange("#/outlook")).toBe("outlook");
  });

  it("lists Next quarter in the sidebar only when a forward quarter is published", () => {
    const { unmount } = render(<App initialDashboard={makeTestDashboard()} />);
    expect(screen.queryByRole("link", { name: "Next quarter" })).toBeNull();
    unmount();
    render(<App initialDashboard={withForward(makeTestDashboard()).dashboard} />);
    expect(screen.getByRole("link", { name: "Next quarter" }).getAttribute("href")).toBe("#/outlook");
  });
});
