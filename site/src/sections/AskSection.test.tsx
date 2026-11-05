import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import { makeTestDashboard } from "../data/testDashboard";
import type { ClaimView, Dashboard, QaAnswer, QaSet, QuarterView } from "../data/types";
import { AskSection } from "./AskSection";

/** Invented answers for these tests only. Numbers are round and not from any filing. */
const questions = [
  "What drove the revenue variance versus forecast this quarter?",
  "How did gross margin compare with the forecast?",
  "Where did operating expenses land against plan?",
  "Which driver moved free cash flow the most?",
  "Did the scenarios bracket the actual result?",
  "How large was the capex variance?",
  "How often did the base forecast miss revenue by more than 10 percent?",
  "Which metric had the largest average miss across the backtest?",
  "Did leasing revenue help or hurt the quarter?",
  "What should a reader check next?",
];

function claim(overrides: Partial<ClaimView>): ClaimView {
  return {
    metric: "total_revenue",
    period: "2026-Q3",
    value: 12.34,
    unit: "USD billion",
    sentence_ref: "1",
    status: "verified",
    expected: 12340000000,
    expected_unit: "USD",
    source: "Form 10-Q, revenue",
    source_url: "https://example.com/10q",
    ...overrides,
  };
}

const answers: QaAnswer[] = questions.map((question, index) => {
  const number = index + 1;
  if (number === 1) {
    return {
      number,
      question,
      text: "Revenue was $12.34B against a forecast of $11.00B. Volume explains most of the gap.",
      claims: [claim({ value: 12.34, sentence_ref: "1" })],
    };
  }
  if (number === 2) {
    return {
      number,
      question,
      text: "Gross margin was 18.5% against a forecast of 19.0%.",
      claims: [
        claim({
          metric: "gross_margin",
          value: 18.5,
          unit: "percent",
          sentence_ref: "1",
          source: null,
          source_url: null,
        }),
      ],
    };
  }
  return {
    number,
    question,
    text: `Answer ${number} is short and has no figures.`,
    claims: [],
  };
});

const qaSet = {
  quarter: "2026-Q3",
  answers,
  verification: { verified: 2, flagged: 0, unsupported: 0 },
} as QaSet;

function dashboardWith(qa: QaSet | null): Dashboard {
  return { ...makeTestDashboard(), latest_quarter: "2026-Q3", qa };
}

function quarterView(id: string): QuarterView {
  const view = makeTestDashboard().quarters.find((item) => item.quarter === id);
  if (!view) throw new Error(`no test quarter ${id}`);
  return view;
}

const latest = () => quarterView("2026-Q3");
const earlier = () => quarterView("2025-Q4");

function questionButton(number: number): HTMLElement {
  return screen.getByRole("button", { name: new RegExp(`^${number}\\. `) });
}

function panelOf(button: HTMLElement): HTMLElement {
  const panel = document.getElementById(button.getAttribute("aria-controls") ?? "");
  if (!panel) throw new Error("aria-controls does not point at a panel");
  return panel;
}

describe("AskSection", () => {
  test("lists the ten questions, each collapsed with aria-expanded", () => {
    const { container } = render(
      <AskSection dashboard={dashboardWith(qaSet)} quarter={latest()} onSelectQuarter={vi.fn()} />,
    );

    expect(screen.getByRole("heading", { level: 2, name: "Ask the analyst" })).toBeTruthy();
    expect(
      screen.getByText(
        "Ten questions, answered by the pipeline's model from the computed tables and checked by code. Visitors do not call the model.",
      ),
    ).toBeTruthy();

    const buttons = container.querySelectorAll<HTMLButtonElement>(".ask-question");
    expect(buttons).toHaveLength(10);
    buttons.forEach((button) => expect(button.getAttribute("aria-expanded")).toBe("false"));
    expect(questionButton(1).textContent).toContain("1. What drove the revenue variance versus forecast this quarter?");
    expect(questionButton(1).querySelector(".ask-indicator")?.textContent).toBe("+");
  });

  test("expands and collapses one answer, and several can be open at once", async () => {
    const user = userEvent.setup();
    render(<AskSection dashboard={dashboardWith(qaSet)} quarter={latest()} onSelectQuarter={vi.fn()} />);

    const first = questionButton(1);
    const second = questionButton(2);

    await user.click(first);
    expect(first.getAttribute("aria-expanded")).toBe("true");
    expect(first.querySelector(".ask-indicator")?.textContent).toBe("−");
    expect(panelOf(first).textContent).toContain("Volume explains most of the gap.");

    await user.click(second);
    expect(second.getAttribute("aria-expanded")).toBe("true");
    expect(first.getAttribute("aria-expanded")).toBe("true");

    await user.click(first);
    expect(first.getAttribute("aria-expanded")).toBe("false");
    expect(second.getAttribute("aria-expanded")).toBe("true");
  });

  test("renders the answer through NarrativeText with a tick on each claimed figure", async () => {
    const user = userEvent.setup();
    render(<AskSection dashboard={dashboardWith(qaSet)} quarter={latest()} onSelectQuarter={vi.fn()} />);

    await user.click(questionButton(1));
    const panel = panelOf(questionButton(1));
    const ticks = panel.querySelectorAll(".tick-number");
    expect(ticks).toHaveLength(1);
    expect(ticks[0].textContent).toContain("12.34");
    expect(panel.querySelector(".narrative")).not.toBeNull();
  });

  test("shows a source link from the first claim that has a source_url, and no line otherwise", async () => {
    const user = userEvent.setup();
    render(<AskSection dashboard={dashboardWith(qaSet)} quarter={latest()} onSelectQuarter={vi.fn()} />);

    await user.click(questionButton(1));
    const link = within(panelOf(questionButton(1))).getByRole("link", { name: "Form 10-Q, revenue" });
    expect(link.getAttribute("href")).toBe("https://example.com/10q");

    await user.click(questionButton(2));
    expect(within(panelOf(questionButton(2))).queryByRole("link")).toBeNull();
    expect(panelOf(questionButton(2)).textContent).not.toContain("Source:");
  });

  test("an earlier quarter shows the note and a switch that selects the Q&A quarter, with the list kept", async () => {
    const user = userEvent.setup();
    const onSelectQuarter = vi.fn();
    const { container } = render(
      <AskSection dashboard={dashboardWith(qaSet)} quarter={earlier()} onSelectQuarter={onSelectQuarter} />,
    );

    expect(screen.getByText("These answers cover Q3 2026 only.")).toBeTruthy();
    expect(container.querySelectorAll(".ask-question")).toHaveLength(10);

    await user.click(screen.getByRole("button", { name: "Show Q3 2026" }));
    expect(onSelectQuarter).toHaveBeenCalledTimes(1);
    expect(onSelectQuarter).toHaveBeenCalledWith("2026-Q3");
  });

  test("the latest quarter shows no note", () => {
    render(<AskSection dashboard={dashboardWith(qaSet)} quarter={latest()} onSelectQuarter={vi.fn()} />);

    expect(screen.queryByText(/These answers cover/)).toBeNull();
    expect(screen.queryByRole("button", { name: /^Show / })).toBeNull();
  });

  test("with no Q&A set it shows the empty state and no questions", () => {
    const { container } = render(
      <AskSection dashboard={dashboardWith(null)} quarter={latest()} onSelectQuarter={vi.fn()} />,
    );

    expect(
      screen.getByText(
        "The answers have not been written yet. They appear after the next full pipeline run, each checked against the filings.",
      ),
    ).toBeTruthy();
    expect(container.querySelectorAll(".ask-question")).toHaveLength(0);
  });

  test("questions 7 and 8 carry the quiet 'Uses all 12 quarters' tag, and no others do", () => {
    const { container } = render(
      <AskSection dashboard={dashboardWith(qaSet)} quarter={latest()} onSelectQuarter={vi.fn()} />,
    );

    const tags = container.querySelectorAll(".ask-tag");
    expect(tags).toHaveLength(2);
    tags.forEach((tag) => expect(tag.textContent).toBe("Uses all 12 quarters"));
    const tagged = Array.from(tags, (tag) => tag.closest(".ask-item")?.querySelector(".ask-number")?.textContent);
    expect(tagged).toEqual(["7.", "8."]);
  });
});
