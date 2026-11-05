/** Totals over every figure the model wrote on the page, from the published dashboard. */
import type { Dashboard, VerificationCounts } from "../data/types";

const ZERO: VerificationCounts = { verified: 0, flagged: 0, unsupported: 0, total: 0 };

/** Every figure the model wrote on the page: all memos plus the answers. */
export function commentaryTotals(dashboard: Dashboard): VerificationCounts {
  const counts = [
    ...dashboard.quarters.map((quarter) => quarter.memo?.verification ?? ZERO),
    dashboard.qa?.verification ?? ZERO,
  ];
  return counts.reduce(
    (sum, item) => ({
      verified: sum.verified + item.verified,
      flagged: sum.flagged + item.flagged,
      unsupported: sum.unsupported + item.unsupported,
      total: sum.total + item.total,
    }),
    ZERO,
  );
}
