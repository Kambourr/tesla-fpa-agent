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

  it("still ticks a figure whose sentence_ref points past the text", () => {
    const { container } = render(
      <NarrativeText text={TEXT} claims={[claim({ value: 28.05, sentence_ref: "5" })]} />,
    );
    expect(wrappedTexts(container)).toEqual(["$28.05B"]);
    expect(screen.queryByRole("region", { name: "Figures not found in the text" })).toBeNull();
  });

  it("ticks figures when the model numbers sentences one too high", () => {
    // Live narration counted a clause after a semicolon as its own sentence,
    // so every later claim pointed one sentence too far.
    const text =
      "Revenue was $28.05 billion; leasing rose. Gross profit was $5.49 billion. Margin was 19.6%.";
    const { container } = render(
      <NarrativeText
        text={text}
        claims={[
          claim({ value: 28.05, sentence_ref: "1" }),
          claim({ metric: "actual.gross_profit", value: 5.49, sentence_ref: "3" }),
          claim({ metric: "actual.gross_margin", value: 19.6, unit: "percent", sentence_ref: "4" }),
        ]}
      />,
    );
    expect(wrappedTexts(container)).toEqual(["$28.05 billion", "$5.49 billion", "19.6%"]);
    expect(screen.queryByRole("region", { name: "Figures not found in the text" })).toBeNull();
  });

  it("lets two claims with the same value share one written figure", () => {
    const text = "Capital expenditures were $1.50 billion above forecast.";
    const { container } = render(
      <NarrativeText
        text={text}
        claims={[
          claim({ metric: "variance.purchases_of_property_and_equipment", value: 1.5 }),
          claim({ metric: "bridge.free_cash_flow.purchases_of_property_and_equipment", value: 1.5 }),
        ]}
      />,
    );
    expect(wrappedTexts(container)).toEqual(["$1.50 billion"]);
    expect(screen.queryByRole("region", { name: "Figures not found in the text" })).toBeNull();
  });

  it("still lists a same-valued claim whose verification result differs", () => {
    const text = "Capital expenditures were $1.50 billion above forecast.";
    render(
      <NarrativeText
        text={text}
        claims={[
          claim({ value: 1.5 }),
          claim({ metric: "variance.other", value: 1.5, status: "flagged", expected: 2e9 }),
        ]}
      />,
    );
    expect(screen.getByRole("region", { name: "Figures not found in the text" })).toBeTruthy();
  });

  it("lets a claim keep the token in its own sentence before a fallback claim can take it", () => {
    const text = "Gross profit fell $1.14 billion. The automotive bar fell $1.14 billion.";
    const { container } = render(
      <NarrativeText
        text={text}
        claims={[
          claim({ metric: "bridge.gross_profit.automotive", value: -1.14, sentence_ref: "9" }),
          claim({ metric: "variance.gross_profit", value: -1.14, sentence_ref: "1" }),
        ]}
      />,
    );
    const metrics = Array.from(container.querySelectorAll("p.narrative .tick-number")).length;
    expect(metrics).toBe(2);
    expect(screen.queryByRole("region", { name: "Figures not found in the text" })).toBeNull();
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
    expect(numberCandidates(486532).slice(0, 2)).toEqual(["486,532", "486532"]);
  });

  it("adds the trailing-zero spellings prose uses", () => {
    expect(numberCandidates(1.5)).toEqual(["1.5", "1.50"]);
    expect(numberCandidates(20)).toContain("20.0");
    expect(numberCandidates(-1.14)).toEqual(["1.14"]);
  });
});
