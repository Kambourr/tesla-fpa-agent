import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ClaimView, Dashboard, QuarterView } from "../data/types";
import { makeTestDashboard } from "../data/testDashboard";
import { BuildChain } from "./BuildChain";
import { HeroQuote } from "./HeroQuote";
import { buildSteps, commentaryTotals, heroSentence } from "./heroModel";

function claim(overrides: Partial<ClaimView>): ClaimView {
  return {
    metric: "actual.total_revenue",
    period: "2026-Q3",
    value: 28.05,
    unit: "USD billion",
    sentence_ref: "1",
    status: "verified",
    expected: 28046000000,
    expected_unit: "USD",
    source: "10-Q 0000000000-26-000001",
    source_url: "https://example.com/filing",
    ...overrides,
  };
}

function withMemo(dashboard: Dashboard): { dashboard: Dashboard; quarter: QuarterView } {
  const quarter: QuarterView = {
    ...dashboard.quarters[1],
    memo: {
      text: "Revenue was $28.05 billion, $7.48 billion below forecast. Margin rose.",
      claims: [
        claim({}),
        claim({ metric: "variance.total_revenue", value: -7.48 }),
        claim({ metric: "variance.gross_margin", value: 0.9, sentence_ref: "2" }),
      ],
      verification: { verified: 3, flagged: 0, unsupported: 0, total: 3 },
    },
  };
  return {
    dashboard: {
      ...dashboard,
      quarters: [dashboard.quarters[0], quarter],
      qa: {
        quarter: quarter.quarter,
        answers: [{ number: 1, question: "Why?", text: "Because.", claims: [] }],
        verification: { verified: 1, flagged: 1, unsupported: 0, total: 2 },
      },
    },
    quarter,
  };
}

describe("heroModel", () => {
  it("sums every memo and the answers", () => {
    const { dashboard } = withMemo(makeTestDashboard());
    expect(commentaryTotals(dashboard)).toEqual({ verified: 4, flagged: 1, unsupported: 0, total: 5 });
  });

  it("takes the memo's first sentence and only its claims", () => {
    const { quarter } = withMemo(makeTestDashboard());
    const sentence = heroSentence(quarter);
    expect(sentence?.text).toBe("Revenue was $28.05 billion, $7.48 billion below forecast.");
    expect(sentence?.claims.map((item) => item.metric)).toEqual([
      "actual.total_revenue",
      "variance.total_revenue",
    ]);
    expect(sentence?.form).toBe("10-Q");
  });

  it("states each step with real counts and falls back without inventing one", () => {
    const { dashboard } = withMemo(makeTestDashboard());
    const steps = buildSteps(dashboard);
    expect(steps.map((step) => step.number)).toEqual([1, 2, 3, 4, 5]);
    expect(steps[0].detail).toBe("100 facts from 10 SEC filings, plus 8 quarters of delivery releases.");
    expect(steps[1].detail).toBe("1 quarter, each forecast as of the day the prior quarter was filed.");
    expect(steps[2].detail).toBe("1 variance bridge; the model wrote 1 memo and 1 answer.");
    expect(steps[3].detail).toBe("5 figures checked by code against the filings; 1 did not tie.");
    expect(steps[4].detail).toBe("One command runs the whole pipeline and publishes this page.");

    const full = { ...dashboard.run, duration_seconds: 422.55, estimated_cost_usd: 0.0335, model: "m" };
    expect(buildSteps({ ...dashboard, last_full_run: full })[4].detail).toBe(
      "A full run takes 7 min 3 s and $0.03 of model use; one click refreshes the page.",
    );

    const older = { ...dashboard } as Partial<Dashboard>;
    delete older.sources;
    expect(buildSteps(older as Dashboard)[0].detail).toBe(
      "Tesla's 10-Q and 10-K filings from SEC EDGAR, plus the quarterly delivery releases.",
    );
  });
});

describe("HeroQuote", () => {
  it("shows the model's sentence with a tick on each figure and the check line", () => {
    const { dashboard, quarter } = withMemo(makeTestDashboard());
    const { container } = render(
      <HeroQuote dashboard={dashboard} quarter={quarter} onSelectQuarter={() => undefined} />,
    );
    expect(container.querySelectorAll("blockquote .tick-number")).toHaveLength(2);
    expect(screen.getByText(/Written by an AI model from Tesla's 10-Q for Q3 2026\./)).toBeTruthy();
    expect(screen.getByText(/4 of 5 tie to the filings, 1 flagged and shown as flagged\./)).toBeTruthy();
  });

  it("says the memo is not written yet when there is none", () => {
    const dashboard = makeTestDashboard();
    render(
      <HeroQuote dashboard={dashboard} quarter={dashboard.quarters[1]} onSelectQuarter={() => undefined} />,
    );
    expect(screen.getByText(/has not been written yet/)).toBeTruthy();
  });
});

describe("BuildChain", () => {
  it("renders the five steps in order with the stack and a link to the author", () => {
    const { dashboard, quarter } = withMemo(makeTestDashboard());
    render(<BuildChain dashboard={dashboard} quarter={quarter} onSelectQuarter={() => undefined} />);
    const titles = screen.getAllByRole("heading", { level: 3 }).map((item) => item.textContent);
    expect(titles).toEqual(["Pulled", "Forecast", "Explained", "Checked", "Shipped"]);
    expect(screen.getByRole("link", { name: "Jacob Kambour" }).getAttribute("href")).toBe("#about-title");
  });
});
