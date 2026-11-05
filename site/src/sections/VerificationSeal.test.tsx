import { render } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import type { QaSet, QuarterView, VerificationCounts } from "../data/types";
import { makeTestDashboard } from "../data/testDashboard";
import { MethodSection } from "../components/MethodSection";
import { VerificationSeal } from "./VerificationSeal";
import { commentaryCounts, sealSentence } from "./VerificationSealFormat";

// Every number here is invented. The page itself reads only dashboard.json.
const base = makeTestDashboard();
const QUARTER_ID = base.quarters[0].quarter;
const OTHER_QUARTER_ID = "invented-other-quarter";

function counts(verified: number, flagged: number, unsupported: number): VerificationCounts {
  return { verified, flagged, unsupported, total: verified + flagged + unsupported };
}

function quarterWith(memo: VerificationCounts | null): QuarterView {
  const memoView = memo === null ? null : { text: "Invented memo text.", claims: [], verification: memo };
  return { ...base.quarters[0], quarter: QUARTER_ID, memo: memoView };
}

function qaWith(quarter: string, verification: VerificationCounts): QaSet {
  return { quarter, answers: [], verification };
}

function renderSeal(quarter: QuarterView, qa: QaSet | null, drawn = true) {
  return render(<VerificationSeal quarter={quarter} qa={qa} drawn={drawn} />);
}

function sealText(container: HTMLElement): string {
  return container.querySelector(".seal-text")?.textContent ?? "";
}

function markCount(container: HTMLElement, selector = ".seal-mark"): number {
  return container.querySelectorAll(selector).length;
}

describe("VerificationSeal counts and wording", () => {
  test("states verified out of total and appends flagged and unsupported counts", () => {
    const { container } = renderSeal(quarterWith(counts(4, 2, 1)), null);
    expect(sealText(container)).toBe(
      "4 of 7 figures in the commentary tie to the filings, 2 flagged, 1 unsupported.",
    );
  });

  test("draws one tick per verified figure, capped at five, and one flag when figures are open", () => {
    const { container } = renderSeal(quarterWith(counts(4, 2, 1)), null);
    expect(markCount(container, ".seal-mark:not(.seal-flag)")).toBe(4);
    expect(markCount(container, ".seal-flag")).toBe(1);
    expect(container.querySelector(".seal-flag .tick-icon-flagged")).not.toBeNull();
  });

  test("with every figure verified, states the count with no flag text and no flag glyph", () => {
    const { container } = renderSeal(quarterWith(counts(3, 0, 0)), null);
    expect(sealText(container)).toBe("3 of 3 figures in the commentary tie to the filings.");
    expect(markCount(container, ".seal-flag")).toBe(0);
    expect(markCount(container, ".seal-mark")).toBe(3);
  });

  test("caps the tick glyphs at five but keeps the real count in the text", () => {
    const { container } = renderSeal(quarterWith(counts(12, 0, 0)), null);
    expect(sealText(container)).toBe("12 of 12 figures in the commentary tie to the filings.");
    expect(markCount(container, ".seal-mark")).toBe(5);
  });

  test("uses the singular when the commentary has one figure", () => {
    expect(sealSentence(counts(1, 0, 0))).toBe("1 of 1 figure in the commentary ties to the filings.");
  });

  test("keeps the tick glyphs out of the accessible text", () => {
    const { container } = renderSeal(quarterWith(counts(2, 1, 0)), null);
    expect(container.querySelector(".seal-marks")?.getAttribute("aria-hidden")).toBe("true");
  });
});

describe("VerificationSeal memo and Q&A totals", () => {
  test("sums memo and Q&A figures when the Q&A belongs to the selected quarter", () => {
    const memo = counts(3, 1, 0); // 3 verified, 1 flagged, 4 total
    const qa = counts(5, 0, 1); // 5 verified, 1 unsupported, 6 total
    const totals = commentaryCounts(quarterWith(memo), qaWith(QUARTER_ID, qa));
    expect(totals).toEqual({ verified: 8, flagged: 1, unsupported: 1, total: 10 });

    const { container } = renderSeal(quarterWith(memo), qaWith(QUARTER_ID, qa));
    expect(sealText(container)).toBe(
      "8 of 10 figures in the commentary tie to the filings, 1 flagged, 1 unsupported.",
    );
  });

  test("ignores a Q&A set that belongs to another quarter", () => {
    const memo = counts(3, 1, 0);
    const totals = commentaryCounts(quarterWith(memo), qaWith(OTHER_QUARTER_ID, counts(5, 0, 1)));
    expect(totals).toEqual({ verified: 3, flagged: 1, unsupported: 0, total: 4 });
  });

  test("counts the Q&A alone when the quarter has a Q&A but no memo", () => {
    const totals = commentaryCounts(quarterWith(null), qaWith(QUARTER_ID, counts(2, 0, 0)));
    expect(totals).toEqual({ verified: 2, flagged: 0, unsupported: 0, total: 2 });
  });
});

describe("VerificationSeal empty state", () => {
  test("says the commentary is not written yet when there is no memo and no Q&A", () => {
    const { container } = renderSeal(quarterWith(null), null);
    expect(sealText(container)).toBe(
      "The commentary has not been written yet, so no figures are checked for this quarter.",
    );
    expect(markCount(container)).toBe(0);
  });

  test("still shows the empty state when the only Q&A belongs to another quarter", () => {
    const { container } = renderSeal(quarterWith(null), qaWith(OTHER_QUARTER_ID, counts(2, 0, 0)));
    expect(sealText(container)).toMatch(/^The commentary has not been written yet/);
    expect(container.querySelector(".seal-link")).not.toBeNull();
  });
});

describe("VerificationSeal link and motion", () => {
  test("links to the id that the methods section renders", () => {
    const { container } = render(
      <>
        <VerificationSeal quarter={quarterWith(counts(1, 0, 0))} qa={null} drawn />
        <MethodSection />
      </>,
    );
    const link = container.querySelector<HTMLAnchorElement>(".seal-link");
    expect(link?.textContent).toBe("See how the figures are checked");
    const href = link?.getAttribute("href") ?? "";
    expect(href.startsWith("#")).toBe(true);
    const target = container.querySelector(href);
    expect(target).not.toBeNull();
    expect(target?.closest(".method")).not.toBeNull();
  });

  test("the empty state links to the methods section too", () => {
    const { container } = render(
      <>
        <VerificationSeal quarter={quarterWith(null)} qa={null} drawn />
        <MethodSection />
      </>,
    );
    const href = container.querySelector(".seal-link")?.getAttribute("href") ?? "";
    expect(href).toBe("#method-title");
    expect(container.querySelector(href)?.closest(".method")).not.toBeNull();
  });

  test("ticks wait for the bridge to draw", () => {
    const before = renderSeal(quarterWith(counts(2, 0, 0)), null, false);
    expect(before.container.querySelector(".verification-seal")?.hasAttribute("data-drawn")).toBe(false);
    before.unmount();

    const after = renderSeal(quarterWith(counts(2, 0, 0)), null, true);
    expect(after.container.querySelector(".verification-seal")?.getAttribute("data-drawn")).toBe("true");
  });
});
