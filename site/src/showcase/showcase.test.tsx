import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import published from "../../public/data/dashboard.json";
import type { Dashboard, FirstDrafts } from "../data/types";
import { formatCost, formatRunTime, formatStageSeconds } from "../sections/AgentRunFormat";
import { BreakIt, missText, nudged } from "./BreakIt";
import { buildExcerpt, editedValueText } from "./breakItModel";
import { OutputTabs } from "./OutputTabs";
import { FirstDraftLine, issueText, Pipeline } from "./Pipeline";

const live = published as unknown as Dashboard;
const latest = live.quarters.find((item) => item.quarter === live.latest_quarter)!;

describe("breakItModel", () => {
  it("cuts the memo into text and editable figures with their claims", () => {
    const excerpt = buildExcerpt(latest)!;
    expect(excerpt.figures.length).toBeGreaterThan(2);
    const first = excerpt.figures[0];
    expect(Number(first.number.replace(/,/g, ""))).toBeCloseTo(Math.abs(first.claim.value));
    const text = excerpt.pieces
      .map((piece) => (piece.kind === "text" ? piece.text : piece.figure.prefix + piece.figure.number + piece.figure.suffix))
      .join("");
    expect(latest.memo!.text.startsWith(text.trim())).toBe(true);
  });

  it("keeps the claim's sign for a magnitude and flips it for a minus", () => {
    const figure = buildExcerpt(latest)!.figures.find((item) => item.claim.value < 0)!;
    expect(editedValueText(figure, "7.48")).toBe("-7.48");
    expect(editedValueText(figure, "-7.48")).toBe("7.48");
    expect(editedValueText(figure, "1,234.5")).toBe("-1234.5");
  });

  it("suggests a nearby figure and states the size of a miss", () => {
    expect(nudged("28.05")).toBe("28.89");
    expect(nudged("134.8")).toBe("138.8");
    expect(missText(29e9, 28.046e9, "USD")).toBe(" Off by 3.4%.");
    expect(missText(20.0, 19.6, "percent")).toBe(" Off by 0.40 points.");
    expect(missText(28.046e9, 28.046e9, "USD")).toBe("");
  });
});

describe("BreakIt", () => {
  it("flags an edited figure, explains it, and restores the model's figures", () => {
    render(<BreakIt dashboard={live} quarter={latest} />);
    const inputs = screen.getAllByRole("textbox");
    const result = () => document.getElementById("breakit-result")!.textContent ?? "";
    expect(result()).toMatch(/^Ties\./);
    fireEvent.change(inputs[0], { target: { value: "29" } });
    expect(result()).toMatch(/^Flagged\./);
    expect(result()).toMatch(/Off by/);
    fireEvent.click(screen.getByRole("button", { name: "Restore the model's figures" }));
    expect(result()).toMatch(/^Ties\./);
  });

  it("a unit change alone is caught", () => {
    render(<BreakIt dashboard={live} quarter={latest} />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "USD million" } });
    expect(document.getElementById("breakit-result")!.textContent).toMatch(/^Flagged\./);
  });

  it("says there is nothing to test without a memo", () => {
    render(<BreakIt dashboard={live} quarter={{ ...latest, memo: null }} />);
    expect(screen.getByText(/has not been written yet/)).toBeTruthy();
  });
});

describe("Pipeline", () => {
  it("opens each stage's artifact, by click and by arrow keys", () => {
    render(<Pipeline dashboard={live} quarter={latest} />);
    const tabs = screen.getAllByRole("tab");
    expect(tabs.map((tab) => tab.querySelector(".pipeline-step-title")?.textContent)).toEqual([
      "Pull",
      "Forecast",
      "Explain",
      "Write",
      "Verify",
      "Publish",
    ]);
    fireEvent.click(tabs[2]);
    expect(screen.getByRole("tabpanel").textContent).toMatch(/Difference: \$0\./);
    fireEvent.keyDown(tabs[2], { key: "ArrowRight" });
    expect(tabs[3].getAttribute("aria-selected")).toBe("true");
    expect(within(screen.getByRole("tabpanel")).getByText(/"sentence_ref"/)).toBeTruthy();
    fireEvent.keyDown(tabs[3], { key: "End" });
    expect(tabs[5].getAttribute("aria-selected")).toBe("true");
  });
});

describe("FirstDraftLine", () => {
  const base: FirstDrafts = {
    narratives: 12,
    recorded: 12,
    checked: 348,
    caught: 0,
    guard_hits: 0,
    rejected: 0,
    final_problems: 0,
    catches: [],
    first_issues: [],
    final_issues: [],
  };
  const show = (drafts: FirstDrafts) =>
    render(<FirstDraftLine dashboard={{ ...live, first_drafts: drafts }} />).container.textContent;
  const pastEnd = { quarter: "2026-Q1", text: "memo: sentence_ref 9 is past the 8 sentences" };

  it("states each case without inventing a catch", () => {
    expect(show({ ...base, recorded: 0 })).toMatch(/recorded from the next full run/);
    expect(show(base)).toMatch(/all 348 figures tied on the first try; no draft was sent back/);
    expect(show({ ...base, caught: 9, rejected: 4 })).toMatch(
      /code rejected 9 of 348 figures\. Code sent 4 drafts back; fixed on the second try/,
    );
    expect(show({ ...base, caught: 9, rejected: 4, final_problems: 1, recorded: 10 })).toMatch(
      /1 figure stayed flagged on the page \(10 of 12 narratives recorded\)/,
    );
  });

  it("names a structure problem and says when the retry did not fix it", () => {
    const text = show({ ...base, rejected: 1, first_issues: [pastEnd], final_issues: [pastEnd] });
    expect(text).toMatch(/all 348 figures tied on the first try/);
    expect(text).toMatch(/1 draft back for a figure pointed to sentence 9 of a 8-sentence text/);
    expect(text).toMatch(/published as not verified/);
    expect(issueText("memo has 300 words, outside 150 to 250")).toBe("300 words, outside the 150 to 250 limit");
  });
});

describe("OutputTabs", () => {
  it("shows one output at a time and switches with the tabs", () => {
    render(<OutputTabs dashboard={live} quarter={latest} onSelectQuarter={() => undefined} />);
    expect(screen.getByRole("heading", { name: "Revenue, forecast to actual" })).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "Analyst memo" }));
    expect(screen.getByRole("heading", { name: "Analyst memo" })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Revenue, forecast to actual" })).toBeNull();
  });

  it("opens the tab a link points into", () => {
    window.location.hash = "#method-title";
    render(<OutputTabs dashboard={live} quarter={latest} onSelectQuarter={() => undefined} />);
    expect(screen.getByRole("tab", { name: "Method" }).getAttribute("aria-selected")).toBe("true");
    window.location.hash = "";
  });
});

describe("run formatting", () => {
  it("formats run time, cost, and stage seconds", () => {
    expect(formatRunTime(422.55)).toBe("7 min 3 s");
    expect(formatRunTime(18)).toBe("18 seconds");
    expect(formatCost(0.0335)).toBe("$0.03");
    expect(formatStageSeconds(405.7)).not.toBeNull();
  });
});
