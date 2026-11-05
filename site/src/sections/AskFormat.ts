import type { ClaimView, Dashboard, QuarterView } from "../data/types";

/** Questions 7 and 8 draw on the backtest across all 12 published quarters. */
export function usesAllQuarters(questionNumber: number): boolean {
  return questionNumber === 7 || questionNumber === 8;
}

/** The label of the quarter the answers cover, falling back to its id. */
export function answersQuarterLabel(dashboard: Dashboard, quarterId: string): string {
  return dashboard.quarters.find((quarter) => quarter.quarter === quarterId)?.label ?? quarterId;
}

/** The first claim that links to a source, if any. */
export function firstSourcedClaim(claims: ClaimView[]): ClaimView | undefined {
  return claims.find((claim) => claim.source_url);
}

/** True when the selected quarter is not the one the Q&A set was written for. */
export function isOtherQuarter(quarter: QuarterView, answersQuarter: string): boolean {
  return quarter.quarter !== answersQuarter;
}
