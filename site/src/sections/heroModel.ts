/**
 * Data for the hero quote and the "What went into it" chain, derived only from
 * the published dashboard. Every count shown on the page comes from here; when
 * a value is missing (an older dashboard.json without `sources`, or no run yet),
 * the copy falls back to a sentence without that number rather than inventing one.
 */
import type { ClaimView, Dashboard, QuarterView, VerificationCounts } from "../data/types";
import { splitSentences } from "../components/ticks/NarrativeText";
import { formatCost, formatRunTime } from "./AgentRunFormat";

export type HeroSentence = {
  text: string;
  claims: ClaimView[];
  quarterLabel: string;
  form: string | null;
};

export type BuildStep = {
  number: number;
  title: string;
  detail: string;
};

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

/**
 * The first sentence of the selected quarter's memo, with only the claims the
 * model tied to sentence 1, so every tick in the hero belongs to that sentence.
 */
export function heroSentence(quarter: QuarterView): HeroSentence | null {
  const memo = quarter.memo;
  if (!memo) {
    return null;
  }
  const [first] = splitSentences(memo.text);
  if (!first) {
    return null;
  }
  return {
    text: first.text,
    claims: memo.claims.filter((claim) => claim.sentence_ref === "1"),
    quarterLabel: quarter.label,
    form: quarter.filing?.form ?? null,
  };
}

function count(value: number): string {
  return value.toLocaleString("en-US");
}

function plural(value: number, one: string, many: string): string {
  return `${count(value)} ${value === 1 ? one : many}`;
}

export function buildSteps(dashboard: Dashboard): BuildStep[] {
  const backtests = dashboard.quarters.filter((quarter) => quarter.kind === "backtest");
  const forecasted = backtests.filter((quarter) => quarter.has_forecast);
  const bridges = forecasted.reduce(
    (sum, quarter) =>
      sum + Object.values(quarter.bridges).filter((bars) => bars && bars.length > 0).length,
    0,
  );
  const memos = backtests.filter((quarter) => quarter.memo).length;
  const answers = dashboard.qa?.answers.length ?? 0;
  const totals = commentaryTotals(dashboard);
  const sources = dashboard.sources;
  const runTime = formatRunTime(dashboard.run.duration_seconds);
  const cost = formatCost(dashboard.run.estimated_cost_usd);
  const ranFully = dashboard.run.model !== null;

  const pulled =
    sources && sources.facts > 0
      ? `${count(sources.facts)} facts from ${plural(sources.filings, "SEC filing", "SEC filings")}, plus ${plural(sources.delivery_quarters, "quarter", "quarters")} of delivery releases.`
      : "Tesla's 10-Q and 10-K filings from SEC EDGAR, plus the quarterly delivery releases.";
  const explained =
    memos > 0
      ? `${plural(bridges, "variance bridge", "variance bridges")}; the model wrote ${plural(memos, "memo", "memos")} and ${plural(answers, "answer", "answers")}.`
      : `${plural(bridges, "variance bridge", "variance bridges")}, each summing exactly to its variance.`;
  const checked =
    totals.total > 0
      ? `${plural(totals.total, "figure", "figures")} checked by code against the filings; ${count(totals.flagged + totals.unsupported)} did not tie.`
      : "Every figure the model writes is checked by code against the filings.";
  const shipped =
    ranFully && runTime && cost
      ? `${runTime} end to end and ${cost} of model use, refreshed in one click.`
      : "One command runs the whole pipeline and publishes this page.";

  return [
    { number: 1, title: "Pulled", detail: pulled },
    {
      number: 2,
      title: "Forecast",
      detail: `${plural(forecasted.length, "quarter", "quarters")}, each forecast as of the day the prior quarter was filed.`,
    },
    { number: 3, title: "Explained", detail: explained },
    { number: 4, title: "Checked", detail: checked },
    { number: 5, title: "Shipped", detail: shipped },
  ];
}
