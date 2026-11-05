import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { makeTestDashboard } from "../data/testDashboard";
import type { Memo, QuarterView } from "../data/types";
import { MemoSection } from "./MemoSection";

const MEMO: Memo = {
  text:
    "Revenue came in at $28.05B, below the forecast. Operating income moved −21.1% against the forecast. Deliveries were 486,532 units.",
  claims: [
    {
      metric: "actual.total_revenue",
      period: "2026-Q3",
      value: 28.05,
      unit: "USD billion",
      sentence_ref: "1",
      status: "verified",
      expected: 28_046_000_000,
      expected_unit: "USD",
      source: "10-Q 0000000000-26-000001",
      source_url: null,
    },
    {
      metric: "variance_pct.operating_income",
      period: "2026-Q3",
      value: -21.1,
      unit: "percent",
      sentence_ref: "2",
      status: "flagged",
      expected: -20.4,
      expected_unit: "percent",
      source: null,
      source_url: null,
    },
    {
      metric: "actual.deliveries_total",
      period: "2026-Q3",
      value: 486532,
      unit: "units",
      sentence_ref: "3",
      status: "verified",
      expected: 486532,
      expected_unit: "units",
      source: "Tesla P&D release",
      source_url: null,
    },
  ],
  verification: { verified: 2, flagged: 1, unsupported: 0, total: 3 },
};

function quarterWith(memo: Memo | null, label = "Q3 2026"): QuarterView {
  const base = makeTestDashboard().quarters.find((item) => item.quarter === "2026-Q3");
  if (!base) throw new Error("test dashboard has no 2026-Q3 quarter");
  return { ...base, label, memo };
}

function renderMemo(quarter: QuarterView) {
  return render(
    <MemoSection dashboard={makeTestDashboard()} quarter={quarter} onSelectQuarter={() => undefined} />,
  );
}

describe("MemoSection", () => {
  it("shows the memo header lines in sans, with the quarter label", () => {
    renderMemo(quarterWith(MEMO));
    expect(screen.getByRole("heading", { name: "Analyst memo" })).toBeTruthy();
    expect(screen.getByText("To: Readers of this page")).toBeTruthy();
    expect(screen.getByText("Re: Q3 2026 revenue and profit against the forecast")).toBeTruthy();
    expect(screen.getByText("Prepared by: the pipeline's model; every figure checked by code")).toBeTruthy();
  });

  it("renders the tickmark legend beside the memo", () => {
    renderMemo(quarterWith(MEMO));
    const legend = screen.getByRole("region", { name: "Tickmark legend" });
    expect(within(legend).getAllByRole("term")).toHaveLength(3);
  });

  it("puts each claimed figure in the memo body with a tick that has an accessible name", () => {
    const { container } = renderMemo(quarterWith(MEMO));
    const body = container.querySelector(".memo-body");
    expect(body).not.toBeNull();
    expect(body?.querySelectorAll("p.narrative")).toHaveLength(1);
    expect(within(body as HTMLElement).getAllByRole("button", { name: /^Verified: ties to/ })).toHaveLength(2);
    expect(within(body as HTMLElement).getByRole("button", { name: /^Flagged:/ })).toBeTruthy();
  });

  it("shows the count line with the flagged count and no unsupported count", () => {
    const { container } = renderMemo(quarterWith(MEMO));
    const count = container.querySelector(".memo-count");
    expect(count?.textContent).toBe("2 of 3 figures tie to the filings. 1 flagged.");
    expect(screen.queryByText(/unsupported/)).toBeNull();
  });

  it("shows the unsupported count when it is not zero", () => {
    const { container } = renderMemo(
      quarterWith({
        ...MEMO,
        verification: { verified: 2, flagged: 0, unsupported: 1, total: 3 },
      }),
    );
    expect(container.querySelector(".memo-count")?.textContent).toBe(
      "2 of 3 figures tie to the filings. 1 unsupported.",
    );
    expect(container.querySelector(".memo-count-flagged")).toBeNull();
  });

  it("shows the empty state and still the legend when the quarter has no memo", () => {
    renderMemo(quarterWith(null));
    expect(
      screen.getByText(
        "The memo for this quarter has not been written yet. It appears after the next full pipeline run, with every figure checked against the filings.",
      ),
    ).toBeTruthy();
    expect(screen.getByRole("region", { name: "Tickmark legend" })).toBeTruthy();
    expect(screen.queryByText(/figures tie to the filings/)).toBeNull();
  });

  it("shows the selected quarter's memo when the quarter changes", () => {
    const other: Memo = {
      text: "Deliveries rose in the quarter. Margin held steady.",
      claims: [],
      verification: { verified: 0, flagged: 0, unsupported: 0, total: 0 },
    };
    const { rerender } = renderMemo(quarterWith(MEMO));
    expect(screen.getByText("Re: Q3 2026 revenue and profit against the forecast")).toBeTruthy();
    rerender(
      <MemoSection
        dashboard={makeTestDashboard()}
        quarter={quarterWith(other, "Q4 2025")}
        onSelectQuarter={() => undefined}
      />,
    );
    expect(screen.getByText("Re: Q4 2025 revenue and profit against the forecast")).toBeTruthy();
    expect(screen.getByText("Deliveries rose in the quarter. Margin held steady.")).toBeTruthy();
    expect(screen.getByText("0 of 0 figures tie to the filings.")).toBeTruthy();
  });
});
