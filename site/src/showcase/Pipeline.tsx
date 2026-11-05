import { useState, type ReactNode } from "react";
import { formatExpected, metricLabel } from "../components/ticks/tickFormat";
import type { ClaimView, Dashboard, QuarterView, Stage } from "../data/types";
import { formatCost, formatRunTime, formatStageSeconds } from "../sections/AgentRunFormat";
import { commentaryTotals } from "../sections/heroModel";
import { useTabs } from "./useTabs";
import "./Pipeline.css";

const STEPS = ["pull", "forecast", "bridge", "write", "verify", "publish"] as const;
type StepId = (typeof STEPS)[number];
const PANEL_ID = "pipeline-panel";

function count(value: number): string {
  return value.toLocaleString("en-US");
}

function money(value: number | null | undefined): string {
  return value === null || value === undefined ? "n/a" : formatExpected(value, "USD");
}

function json(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

function line(quarter: QuarterView, metric: string) {
  return quarter.lines.find((item) => item.metric === metric) ?? null;
}

/** The claim the artifacts follow: the memo's revenue figure, else its first claim. */
function leadClaim(quarter: QuarterView): ClaimView | null {
  const claims = quarter.memo?.claims ?? [];
  return claims.find((claim) => claim.metric === "actual.total_revenue") ?? claims[0] ?? null;
}

function ruleFor(unit: string | null): string {
  if (unit === "USD" || unit === "USD_per_unit") return "within 0.5%, same sign";
  if (unit === "percent") return "within 0.1 percentage points";
  return "exact at the precision written";
}

interface StepView {
  id: StepId;
  title: string;
  stat: string;
  actor: "Code" | "Model";
  body: ReactNode;
}

function buildSteps(dashboard: Dashboard, quarter: QuarterView): StepView[] {
  const sources = dashboard.sources;
  const totals = commentaryTotals(dashboard);
  const backtests = dashboard.quarters.filter((item) => item.kind === "backtest" && item.has_forecast);
  const memos = backtests.filter((item) => item.memo).length;
  const answers = dashboard.qa?.answers.length ?? 0;
  const bridges = backtests.reduce(
    (sum, item) => sum + Object.values(item.bridges).filter((bars) => bars.length > 0).length,
    0,
  );
  const claim = leadClaim(quarter);
  const revenue = line(quarter, "total_revenue");
  const deliveries = line(quarter, "deliveries");
  const asp = line(quarter, "automotive_asp");
  const margin = line(quarter, "gross_margin");
  const bars = quarter.bridges.revenue ?? [];
  const barSum = bars.reduce((sum, bar) => sum + bar.value, 0);
  const gap = revenue && revenue.actual !== null && revenue.forecast !== null ? revenue.actual - revenue.forecast : null;
  const run = dashboard.last_full_run ?? dashboard.run;
  const runStages = run.stages.filter((stage): stage is Stage & { seconds: number } => stage.seconds !== null);
  const slowest = Math.max(1, ...runStages.map((stage) => stage.seconds));
  const drafts = dashboard.first_drafts;
  const sizeKb = Math.round(JSON.stringify(dashboard).length / 1024);

  return [
    {
      id: "pull",
      title: "Pull",
      actor: "Code",
      stat: sources ? `${count(sources.facts)} facts, ${count(sources.filings)} filings` : "SEC filings",
      body: (
        <>
          <p>
            SEC companyfacts plus each 10-Q and 10-K's XBRL for the segment lines, and{" "}
            {sources ? count(sources.delivery_quarters) : "the"} quarters of delivery counts. Every
            value keeps the filing it came from, and a restatement never overwrites what was first
            reported. The revenue figure the memo cites:
          </p>
          <pre className="pipeline-code">
            {json({
              metric: "total_revenue",
              period: quarter.quarter,
              value: revenue?.actual ?? null,
              form: quarter.filing?.form ?? null,
              accession: quarter.filing?.accession ?? null,
              filed: quarter.filing?.filing_date ?? null,
            })}
          </pre>
          {quarter.filing ? (
            <a href={quarter.filing.url} target="_blank" rel="noreferrer">
              Open the {quarter.filing.form} on SEC EDGAR
            </a>
          ) : null}
        </>
      ),
    },
    {
      id: "forecast",
      title: "Forecast",
      actor: "Code",
      stat: `${backtests.length} quarters, no look-ahead`,
      body: (
        <>
          <p>
            A driver model forecasts each quarter as of the day the previous quarter was filed, so it
            never sees the answer. {quarter.label}, as forecast:
          </p>
          <table className="pipeline-table">
            <tbody>
              <tr>
                <th scope="row">Deliveries</th>
                <td>{deliveries?.forecast != null ? count(Math.round(deliveries.forecast)) : "n/a"}</td>
                <td className="pipeline-quiet">actual {deliveries?.actual != null ? count(Math.round(deliveries.actual)) : "n/a"}</td>
              </tr>
              <tr>
                <th scope="row">Average price</th>
                <td>{asp?.forecast != null ? formatExpected(asp.forecast, "USD_per_unit") : "n/a"}</td>
                <td className="pipeline-quiet">actual {asp?.actual != null ? formatExpected(asp.actual, "USD_per_unit") : "n/a"}</td>
              </tr>
              <tr>
                <th scope="row">Gross margin</th>
                <td>{margin?.forecast != null ? `${margin.forecast.toFixed(1)}%` : "n/a"}</td>
                <td className="pipeline-quiet">actual {margin?.actual != null ? `${margin.actual.toFixed(1)}%` : "n/a"}</td>
              </tr>
              <tr>
                <th scope="row">Revenue</th>
                <td>{money(revenue?.forecast)}</td>
                <td className="pipeline-quiet">actual {money(revenue?.actual)}</td>
              </tr>
            </tbody>
          </table>
        </>
      ),
    },
    {
      id: "bridge",
      title: "Explain",
      actor: "Code",
      stat: `${count(bridges)} bridges that add up`,
      body: (
        <>
          <p>
            Four bridges per quarter split the miss into drivers. They must sum exactly to the
            variance; there is no plug. {quarter.label} revenue:
          </p>
          <table className="pipeline-table">
            <tbody>
              <tr>
                <th scope="row">Forecast</th>
                <td>{money(revenue?.forecast)}</td>
              </tr>
              {bars.map((bar) => (
                <tr key={bar.driver}>
                  <th scope="row">{bar.label}</th>
                  <td className={bar.value < 0 ? "pipeline-down" : "pipeline-up"}>
                    {bar.value >= 0 ? "+" : ""}
                    {money(bar.value)}
                  </td>
                </tr>
              ))}
              <tr className="pipeline-total">
                <th scope="row">Actual</th>
                <td>{money(revenue?.actual)}</td>
              </tr>
            </tbody>
          </table>
          {gap !== null ? (
            <p className="pipeline-check">
              Drivers sum to {money(barSum)}; actual minus forecast is {money(gap)}. Difference:{" "}
              {money(Math.abs(barSum - gap) < 1 ? 0 : barSum - gap)}.
            </p>
          ) : null}
        </>
      ),
    },
    {
      id: "write",
      title: "Write",
      actor: "Model",
      stat: `${memos} memos, ${answers} answers`,
      body: (
        <>
          <p>
            An OpenAI model gets a sheet of computed figures, never the filings, and returns
            structured JSON: the prose plus one claim per number, each citing a key on the sheet. The
            revenue claim behind the memo's first sentence:
          </p>
          <pre className="pipeline-code">
            {claim
              ? json({
                  metric: claim.metric,
                  period: claim.period,
                  value: claim.value,
                  unit: claim.unit,
                  sentence_ref: claim.sentence_ref,
                })
              : "No memo for this quarter yet."}
          </pre>
          <p className="pipeline-quiet">Model: {run.model ?? "not recorded"}. Visitors never call it.</p>
        </>
      ),
    },
    {
      id: "verify",
      title: "Verify",
      actor: "Code",
      stat: `${count(totals.total)} figures checked`,
      body: (
        <>
          <p>
            Code looks up each claim's key and compares. A miss goes back to the model once with the
            expected value; anything still wrong is published as flagged, never fixed silently. The
            record for the claim above:
          </p>
          <pre className="pipeline-code">
            {claim
              ? json({
                  status: claim.status,
                  expected: claim.expected,
                  expected_unit: claim.expected_unit,
                  rule: ruleFor(claim.expected_unit),
                  source: claim.source,
                })
              : "No claims for this quarter yet."}
          </pre>
          <FirstDraftLine dashboard={dashboard} />
          {drafts.catches.length > 0 ? (
            <ul className="pipeline-catches">
              {drafts.catches.slice(0, 3).map((item, index) => (
                <li key={index}>
                  {item.quarter} {item.location}: wrote {item.written} {item.unit} for{" "}
                  {metricLabel(item.metric).toLowerCase()}
                  {item.expected !== null && item.expected_unit
                    ? `; source says ${formatExpected(item.expected, item.expected_unit)}`
                    : "; no such figure on the sheet"}
                  .
                </li>
              ))}
            </ul>
          ) : null}
        </>
      ),
    },
    {
      id: "publish",
      title: "Publish",
      actor: "Code",
      stat:
        formatRunTime(run.duration_seconds) && formatCost(run.estimated_cost_usd)
          ? `${formatRunTime(run.duration_seconds)}, ${formatCost(run.estimated_cost_usd)}`
          : "one JSON file",
      body: (
        <>
          <p>
            One command runs every stage and writes a {sizeKb} KB JSON file this static page reads.
            GitHub Actions runs it on demand, commits the file, and redeploys. The last full run:
          </p>
          <ul className="pipeline-bars" aria-label="Seconds per stage in the last full run">
            {runStages.map((stage) => (
              <li key={stage.name}>
                <span className="pipeline-bar-name">{stage.name}</span>
                <span className="pipeline-bar-track" aria-hidden="true">
                  <span
                    className={`pipeline-bar-fill${stage.name === "explain" ? " is-model" : ""}`}
                    style={{ width: `${Math.max(1, (stage.seconds / slowest) * 100)}%` }}
                  />
                </span>
                <span className="pipeline-bar-value">{formatStageSeconds(stage.seconds)}</span>
              </li>
            ))}
          </ul>
          <p className="pipeline-quiet">
            Verified narratives are cached, so a refresh pays only for new or changed quarters.
          </p>
        </>
      ),
    },
  ];
}

export function FirstDraftLine({ dashboard }: { dashboard: Dashboard }) {
  const drafts = dashboard.first_drafts;
  if (!drafts || drafts.recorded === 0) {
    return (
      <p className="pipeline-quiet">
        First-draft results (what the checker rejected before the re-ask) are recorded from the next
        full run.
      </p>
    );
  }
  const scope =
    drafts.recorded < drafts.narratives ? ` (${drafts.recorded} of ${drafts.narratives} narratives recorded)` : "";
  if (drafts.rejected === 0) {
    return (
      <p className="pipeline-first">
        First drafts: {count(drafts.checked)} figures checked, none rejected{scope}.
      </p>
    );
  }
  return (
    <p className="pipeline-first">
      First drafts: code rejected {count(drafts.caught)} of {count(drafts.checked)} figures
      {drafts.guard_hits > 0 ? ` and ${drafts.guard_hits} advice phrases` : ""} in {drafts.rejected}{" "}
      {drafts.rejected === 1 ? "draft" : "drafts"}, sent them back, and{" "}
      {drafts.final_problems === 0
        ? "every one was corrected"
        : `${drafts.final_problems} stayed flagged on the page`}
      {scope}.
    </p>
  );
}

/** The pipeline as six stages; choosing one shows what it actually produced. */
export function Pipeline({ dashboard, quarter }: { dashboard: Dashboard; quarter: QuarterView }) {
  const [selected, setSelected] = useState<StepId>("verify");
  const steps = buildSteps(dashboard, quarter);
  const { onKeyDown, tabProps } = useTabs(STEPS, selected, setSelected);
  const current = steps.find((step) => step.id === selected) ?? steps[0];

  return (
    <section className="pipeline" aria-labelledby="pipeline-title">
      <p className="pipeline-kicker">The pipeline</p>
      <h2 id="pipeline-title" className="pipeline-title">
        Six stages, one command. Open any stage to see what it produced.
      </h2>
      <div className="pipeline-steps" role="tablist" aria-label="Pipeline stages" onKeyDown={onKeyDown}>
        {steps.map((step, index) => (
          <button key={step.id} className={`pipeline-step${step.actor === "Model" ? " is-model" : ""}`} {...tabProps(step.id, PANEL_ID)}>
            <span className="pipeline-step-top">
              <span className="pipeline-step-index">{index + 1}</span>
              <span className="pipeline-step-actor">{step.actor}</span>
            </span>
            <span className="pipeline-step-title">{step.title}</span>
            <span className="pipeline-step-stat">{step.stat}</span>
          </button>
        ))}
      </div>
      <div
        className="pipeline-panel"
        role="tabpanel"
        id={PANEL_ID}
        aria-labelledby={`${PANEL_ID}-tab-${current.id}`}
        tabIndex={0}
      >
        {current.body}
      </div>
    </section>
  );
}
