import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ClaimView } from "../../data/types";
import { NarrativeText, numberCandidates, splitSentences } from "./NarrativeText";

function claim(overrides: Partial<ClaimView>): ClaimView {
  return {
    metric: "actual.total_revenue",
    period: "2026-Q3",
    value: 1,
    unit: "USD billion",
    sentence_ref: "1",
    status: "verified",
    expected: null,
    expected_unit: null,
    source: "10-Q 0000000000-26-000001",
    source_url: null,
    ...overrides,
  };
}

/** The text of every figure wrapped inside the narrative paragraphs, in document order. */
function wrappedTexts(container: HTMLElement): string[] {
  return Array.from(container.querySelectorAll("p.narrative .tick-number .tick-text")).map(
    (node) => node.textContent ?? "",
  );
}

/** Paragraph text without the hidden tooltip copy. */
function paragraphText(paragraph: Element): string {
  const copy = paragraph.cloneNode(true) as Element;
  copy.querySelectorAll(".tick-tooltip").forEach((node) => node.remove());
  return copy.textContent ?? "";
}

const TEXT =
  "Revenue reached $28.05B in the quarter. Operating income moved −21.1% against the forecast.";

describe("NarrativeText", () => {
  it("wraps $28.05B in sentence 1 and −21.1% in sentence 2", () => {
    const { container } = render(
      <NarrativeText
        className="memo"
        text={TEXT}
        claims={[
          claim({ value: 28.05, unit: "USD billion", sentence_ref: "1" }),
          claim({
            metric: "variance_pct.operating_income",
            value: -21.1,
            unit: "percent",
            sentence_ref: "2",
          }),
        ]}
      />,
    );
    expect(wrappedTexts(container)).toEqual(["$28.05B", "−21.1%"]);
    const paragraphs = container.querySelectorAll("p.narrative");
    expect(paragraphs).toHaveLength(1);
    expect(paragraphText(paragraphs[0])).toBe(TEXT);
  });

  it("lists a claim the text does not show under the not-found note, still with its tick", () => {
    const { container } = render(
      <NarrativeText
        text={TEXT}
        claims={[claim({ value: 999.9, unit: "USD billion", sentence_ref: "1", status: "unsupported" })]}
      />,
    );
    expect(wrappedTexts(container)).toEqual([]);
    const note = screen.getByRole("region", { name: "Figures not found in the text" });
    expect(within(note).getByRole("button", { name: /^Unsupported:/ })).toBeTruthy();
    expect(within(note).getByText("$999.9B")).toBeTruthy();
  });

  it("treats a sentence_ref past the text as not found", () => {
    render(<NarrativeText text={TEXT} claims={[claim({ value: 28.05, sentence_ref: "5" })]} />);
    expect(screen.getByRole("region", { name: "Figures not found in the text" })).toBeTruthy();
  });

  it("wraps each token at most once, so two claims with the same number take two occurrences", () => {
    const { container } = render(
      <NarrativeText
        text="Up 21.1% this year, and 21.1% last year."
        claims={[
          claim({ value: 21.1, unit: "percent", sentence_ref: "1" }),
          claim({ value: 21.1, unit: "percent", sentence_ref: "1" }),
        ]}
      />,
    );
    expect(wrappedTexts(container)).toEqual(["21.1%", "21.1%"]);
    expect(screen.queryByRole("region", { name: "Figures not found in the text" })).toBeNull();
  });

  it("does not match 28 inside 28.05, and matches a grouped number with its comma", () => {
    const { container } = render(
      <NarrativeText
        text="Revenue was 28.05B, up from 28 last year. Deliveries reached 486,532."
        claims={[
          claim({ value: 28, unit: "units", sentence_ref: "1" }),
          claim({ value: 486532, unit: "units", sentence_ref: "2" }),
        ]}
      />,
    );
    expect(wrappedTexts(container)).toEqual(["28", "486,532"]);
  });

  it("numbers sentences across paragraphs and starts a new paragraph at a blank line", () => {
    const { container } = render(
      <NarrativeText
        text={"First sentence here.\n\nSecond paragraph has $28.05B."}
        claims={[claim({ value: 28.05, sentence_ref: "2" })]}
      />,
    );
    const paragraphs = container.querySelectorAll("p.narrative");
    expect(paragraphs).toHaveLength(2);
    expect(wrappedTexts(container)).toEqual(["$28.05B"]);
  });
});

describe("splitSentences", () => {
  it("splits on whitespace after . ? or !", () => {
    const sentences = splitSentences("One. Two? Three!  Four.");
    expect(sentences.map((s) => s.text)).toEqual(["One.", "Two?", "Three!", "Four."]);
    expect(sentences.map((s) => s.number)).toEqual([1, 2, 3, 4]);
  });
});

describe("numberCandidates", () => {
  it("gives the plain and grouped spellings of a value", () => {
    expect(numberCandidates(-7.48)).toEqual(["7.48"]);
    expect(numberCandidates(486532)).toEqual(["486,532", "486532"]);
  });
});
