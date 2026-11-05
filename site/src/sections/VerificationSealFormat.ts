import type { QaSet, QuarterView, VerificationCounts } from "../data/types";

/** The most tick glyphs the seal draws. The count in the text is always the real one. */
export const MAX_SEAL_TICKS = 5;

/** The anchor for the methods section. MethodSection's h2 carries this id. */
export const METHOD_ANCHOR = "#method-title";

/**
 * Verification counts for every commentary figure on the selected quarter's page.
 * The memo counts when the quarter has one. The Q&A counts only when it belongs to
 * the same quarter, and then they are added to the memo's counts.
 * Returns null when neither exists: there is no commentary yet.
 */
export function commentaryCounts(quarter: QuarterView, qa: QaSet | null): VerificationCounts | null {
  const qaForQuarter = qa !== null && qa.quarter === quarter.quarter ? qa : null;
  if (quarter.memo === null && qaForQuarter === null) {
    return null;
  }
  const totals: VerificationCounts = { verified: 0, flagged: 0, unsupported: 0, total: 0 };
  for (const part of [quarter.memo?.verification, qaForQuarter?.verification]) {
    if (!part) {
      continue;
    }
    totals.verified += part.verified;
    totals.flagged += part.flagged;
    totals.unsupported += part.unsupported;
    totals.total += part.total;
  }
  return totals;
}

/**
 * The seal sentence. Flagged and unsupported counts are always appended when present,
 * so a figure that does not tie is never hidden behind the verified count.
 */
export function sealSentence(counts: VerificationCounts): string {
  const figures = counts.total === 1 ? "figure" : "figures";
  const ties = counts.total === 1 ? "ties" : "tie";
  let text = `${counts.verified} of ${counts.total} ${figures} in the commentary ${ties} to the filings`;
  if (counts.flagged > 0) {
    text += `, ${counts.flagged} flagged`;
  }
  if (counts.unsupported > 0) {
    text += `, ${counts.unsupported} unsupported`;
  }
  return `${text}.`;
}

/** How many verified tick glyphs to draw: one per verified figure, up to the cap. */
export function sealTickCount(counts: VerificationCounts): number {
  return Math.min(Math.max(counts.verified, 0), MAX_SEAL_TICKS);
}

/** True when at least one figure is flagged or unsupported, so the amber flag shows. */
export function hasOpenFigures(counts: VerificationCounts): boolean {
  return counts.flagged > 0 || counts.unsupported > 0;
}
