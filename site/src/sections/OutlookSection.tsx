import type { Dashboard, QuarterView, Scenario } from "../data/types";
import { buildForecastRows, flexSentence, formatAmount } from "./ForecastSectionFormat";
import "./OutlookSection.css";

const SCENARIOS: { value: Scenario; label: string }[] = [
  { value: "bear", label: "Bear" },
  { value: "base", label: "Base" },
  { value: "bull", label: "Bull" },
];

/** The lines a reader looks at first; the backtest tabs carry the full P&L. */
export const OUTLOOK_METRICS = [
  "deliveries",
  "automotive_asp",
  "total_revenue",
  "gross_margin",
  "operating_income",
  "free_cash_flow",
] as const;

const DATE_FORMAT = new Intl.DateTimeFormat("en-US", {
  month: "long",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});

/** The first published quarter Tesla has not reported yet, if the pipeline forecast one. */
export function forwardQuarter(dashboard: Dashboard): QuarterView | null {
  return dashboard.quarters.find((quarter) => quarter.kind === "forward") ?? null;
}

/** The latest reported quarter's filing: the newest data the forecast is built from. */
export function builtFrom(dashboard: Dashboard): { label: string; form: string; date: string } | null {
  const latest = dashboard.quarters.find((quarter) => quarter.quarter === dashboard.latest_quarter);
  if (!latest?.filing) return null;
  const parsed = new Date(`${latest.filing.filing_date}T00:00:00Z`);
  return {
    label: latest.label,
    form: latest.filing.form,
    date: Number.isNaN(parsed.getTime()) ? latest.filing.filing_date : DATE_FORMAT.format(parsed),
  };
}

export interface OutlookRow {
  metric: string;
  label: string;
  values: Record<Scenario, string>;
}

export function outlookRows(dashboard: Dashboard, quarter: QuarterView): OutlookRow[] {
  const byScenario = Object.fromEntries(
    SCENARIOS.map(({ value }) => [value, buildForecastRows(quarter, dashboard.scenario_flex, value)]),
  ) as Record<Scenario, ReturnType<typeof buildForecastRows>>;
  return OUTLOOK_METRICS.flatMap((metric) => {
    const base = byScenario.base.find((row) => row.metric === metric);
    if (!base || base.forecast === null) return [];
    const values = Object.fromEntries(
      SCENARIOS.map(({ value }) => {
        const row = byScenario[value].find((item) => item.metric === metric);
        return [value, formatAmount(row?.forecast ?? null, base.unit)];
      }),
    ) as Record<Scenario, string>;
    return [{ metric, label: base.label, values }];
  });
}

function percent(value: number | null | undefined): string | null {
  return value === null || value === undefined ? null : `${value.toFixed(1)}%`;
}

/**
 * The next quarter's forecast: built by the same driver model as the backtest,
 * from filings up to the latest one, with no actuals to compare against yet.
 */
export function OutlookSection({ dashboard, quarter }: { dashboard: Dashboard; quarter: QuarterView }) {
  const rows = outlookRows(dashboard, quarter);
  const source = builtFrom(dashboard);
  const revenueError = percent(dashboard.backtest.averages.total_revenue);
  const incomeError = percent(dashboard.backtest.averages.operating_income);

  return (
    <section className="outlook" aria-labelledby="outlook-heading">
      <p className="outlook-badge">Model forecast · not yet reported</p>
      <h2 id="outlook-heading">{quarter.label}: what the model expects</h2>
      <p className="outlook-lede">
        The same driver model as every backtested quarter
        {source ? `, built from filings through Tesla's ${source.label} ${source.form} (filed ${source.date})` : ""}.
        Tesla has not reported {quarter.label} yet, so there is no actual, no variance bridge, and no
        memo to check.
      </p>

      <div className="outlook-table-wrap">
        <table className="outlook-table">
          <caption className="visually-hidden">{`${quarter.label} forecast by scenario`}</caption>
          <thead>
            <tr>
              <th scope="col">Line</th>
              {SCENARIOS.map((scenario) => (
                <th scope="col" key={scenario.value} className={scenario.value === "base" ? "is-base" : undefined}>
                  {scenario.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.metric}>
                <th scope="row">{row.label}</th>
                {SCENARIOS.map((scenario) => (
                  <td key={scenario.value} className={scenario.value === "base" ? "is-base" : undefined}>
                    {row.values[scenario.value]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="outlook-note">{flexSentence(dashboard.scenario_flex)}</p>
      {revenueError ? (
        <p className="outlook-note">
          How much to trust it: across the backtested quarters, the base forecast missed revenue by{" "}
          {revenueError} on average{incomeError ? ` and operating income by ${incomeError}` : ""}. See the
          Accuracy tab.
        </p>
      ) : null}
      <p className="outlook-disclaimer">
        A mechanical forecast from public filings for a portfolio project. It is not Tesla guidance, a
        consensus estimate, or investment advice.
      </p>
    </section>
  );
}
