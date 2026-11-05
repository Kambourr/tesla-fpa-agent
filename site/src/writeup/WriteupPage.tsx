import { MastheadMark } from "../components/MastheadMark";
import { ThemeToggle } from "../components/ThemeToggle";
import { footerDisclaimer, siteName } from "../config";
import type { Dashboard } from "../data/types";
import { formatCost, formatRunDate, formatRunTime } from "../sections/AgentRunFormat";
import { commentaryTotals } from "../sections/heroModel";
import "./Writeup.css";

const DASHBOARD_HREF = "./";

function count(value: number): string {
  return value.toLocaleString("en-US");
}

function percent(value: number | null | undefined): string | null {
  return value === null || value === undefined ? null : `${value.toFixed(1)}%`;
}

/** The facts the page states, read from the published file. Null means "not recorded". */
export function writeupFacts(dashboard: Dashboard) {
  const totals = commentaryTotals(dashboard);
  const backtests = dashboard.quarters.filter(
    (quarter) => quarter.kind === "backtest" && quarter.has_forecast,
  );
  const memos = backtests.filter((quarter) => quarter.memo).length;
  const full = dashboard.last_full_run ?? null;
  const averages = dashboard.backtest.averages;
  return {
    totals,
    quarters: backtests.length,
    memos,
    answers: dashboard.qa?.answers.length ?? 0,
    sources: dashboard.sources ?? null,
    fullRunTime: full ? formatRunTime(full.duration_seconds) : null,
    fullRunCost: full ? formatCost(full.estimated_cost_usd) : null,
    fullRunDate: full ? formatRunDate(full.started_at) : null,
    revenueError: percent(averages.total_revenue),
    grossProfitError: percent(averages.gross_profit),
    operatingIncomeError: percent(averages.operating_income),
  };
}

/**
 * A one-page, plain-language account of the project for a reader with a
 * minute or two: the problem, the split between code and model, what the
 * checker catches, the decisions that mattered, results, and limits.
 */
export function WriteupPage({ dashboard }: { dashboard: Dashboard }) {
  const facts = writeupFacts(dashboard);
  const missed = facts.totals.flagged + facts.totals.unsupported;

  return (
    <>
      <a className="skip" href="#content">
        Skip to content
      </a>
      <header className="masthead">
        <div className="canvas masthead-bar">
          <a className="site-name writeup-home" href={DASHBOARD_HREF}>
            <MastheadMark />
            <span>{siteName}</span>
          </a>
          <div className="masthead-tools">
            <a className="masthead-author writeup-back" href={DASHBOARD_HREF}>
              Open the dashboard
            </a>
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main id="content" className="canvas writeup" tabIndex={-1}>
        <p className="writeup-kicker">How it was built</p>
        <h1 className="writeup-title">
          An AI model writes the variance memo. Code checks every figure it writes.
        </h1>
        <p className="writeup-lede">
          Every quarter, an FP&amp;A analyst rebuilds the forecast, ties the actuals to the filing,
          breaks the miss into drivers, and writes the commentary, then checks every figure by
          hand. AI can draft that commentary in seconds, but finance cannot use numbers it cannot
          check. This project runs the whole loop on Tesla's public filings and makes the checking
          part of the product.
        </p>

        <section className="writeup-section" aria-labelledby="w-split">
          <h2 id="w-split">The split: code does the numbers, the model does the words</h2>
          <ol className="writeup-steps">
            <li>
              <strong>Code pulls the data.</strong>{" "}
              {facts.sources
                ? `${count(facts.sources.facts)} values from ${count(facts.sources.filings)} SEC filings, plus ${count(facts.sources.delivery_quarters)} quarters of delivery releases.`
                : "Tesla's 10-Q and 10-K filings from SEC EDGAR, plus the quarterly delivery releases."}{" "}
              Each value keeps the filing it came from.
            </li>
            <li>
              <strong>Code builds the forecast.</strong> A driver-based model (deliveries, average
              price, segment revenue, margins, spending) forecasts each of the last{" "}
              {count(facts.quarters)} quarters as of the day the previous quarter was filed, so it
              never sees the answer.
            </li>
            <li>
              <strong>Code explains the miss.</strong> Four variance bridges (revenue, gross
              profit, operating income, free cash flow) break each quarter's gap into drivers that
              add up exactly.
            </li>
            <li>
              <strong>The model writes.</strong> It drafts a memo for each quarter and answers ten
              fixed questions, from a sheet of computed figures. It never sees the raw filings, and
              every number it writes must cite a line on that sheet.
            </li>
            <li>
              <strong>Code checks every figure</strong>, then publishes one file that a static page
              reads. Visitors never call the model.
            </li>
          </ol>
        </section>

        <section className="writeup-section" aria-labelledby="w-checker">
          <h2 id="w-checker">What the checker catches</h2>
          <p>
            Each figure the model writes is looked up on the sheet it cited and compared: within
            0.5% for dollars, 0.1 points for percentages, and exact for vehicle counts, at the
            precision written.
          </p>
          <ul className="writeup-list">
            <li>
              <strong>A wrong number</strong>, such as a revenue figure outside tolerance, is
              flagged with the value it should have been.
            </li>
            <li>
              <strong>A number with no source</strong>, one that cites nothing on the sheet, is
              marked as unsupported.
            </li>
            <li>
              <strong>A wrong sign</strong>: a shortfall written as a gain is flagged even when
              the size is right.
            </li>
            <li>
              <strong>Advice</strong>: a keyword guard blocks buy and sell language and price
              targets.
            </li>
          </ul>
          <p>
            The model gets one chance to correct what was flagged. Anything still wrong is
            published as flagged, never quietly fixed. On the page, each figure carries an
            auditor's tick: green when it ties (click it to open the filing), an amber flag when it
            does not, a question mark when it cannot be traced.
          </p>
          <p className="writeup-result">
            {facts.totals.total > 0
              ? `On the latest run, the checker tested ${count(facts.totals.total)} figures across ${count(facts.memos)} memos and ${count(facts.answers)} answers: ${count(facts.totals.verified)} tied${missed > 0 ? `, ${count(missed)} did not and are shown as flagged` : ", none were flagged"}.`
              : "The check results appear here after the next full pipeline run."}
          </p>
        </section>

        <section className="writeup-section" aria-labelledby="w-decisions">
          <h2 id="w-decisions">Decisions that mattered</h2>
          <dl className="writeup-decisions">
            <dt>No look-ahead</dt>
            <dd>
              Each forecast uses only what was filed before it. A backtest that peeks at the answer
              looks accurate and proves nothing.
            </dd>
            <dt>First-reported values</dt>
            <dd>
              The database keeps one value per line, period, and filing, so a later restatement
              never rewrites what the forecast was judged against.
            </dd>
            <dt>Bridges that add up</dt>
            <dd>
              Every bridge sums exactly to the variance it explains. A bridge with a hidden
              "other" bar is the first thing a finance reviewer would question.
            </dd>
            <dt>Flag, don't fix</dt>
            <dd>
              A wrong figure stays visible and marked. Silently correcting it would make the
              checker look better than it is.
            </dd>
            <dt>Cheap to run</dt>
            <dd>
              {facts.fullRunTime && facts.fullRunCost
                ? `A full run takes ${facts.fullRunTime} and costs ${facts.fullRunCost} in model use.`
                : "A full run takes a few minutes and a few cents in model use."}{" "}
              Verified narratives are cached, so a refresh pays only for new or changed quarters.
            </dd>
          </dl>
        </section>

        <section className="writeup-section" aria-labelledby="w-results">
          <h2 id="w-results">How good is the forecast?</h2>
          <p>
            Deliberately simple, and shown honestly. Average absolute error across the{" "}
            {count(facts.quarters)} backtested quarters:
          </p>
          <table className="writeup-table">
            <tbody>
              <tr>
                <th scope="row">Revenue</th>
                <td>{facts.revenueError ?? "Not recorded"}</td>
              </tr>
              <tr>
                <th scope="row">Gross profit</th>
                <td>{facts.grossProfitError ?? "Not recorded"}</td>
              </tr>
              <tr>
                <th scope="row">Operating income</th>
                <td>{facts.operatingIncomeError ?? "Not recorded"}</td>
              </tr>
            </tbody>
          </table>
          <p>
            Operating income is a small number left over after large ones, so a modest revenue miss
            becomes a large percentage miss there. The dashboard shows every quarter, misses
            included. The point is a forecast you can audit, not the best possible one.
          </p>
        </section>

        <section className="writeup-section" aria-labelledby="w-limits">
          <h2 id="w-limits">Limits</h2>
          <ul className="writeup-list">
            <li>Public data only: SEC filings and Tesla's investor-relations releases.</li>
            <li>
              Delivery counts are typed in from each quarter's first release, with a source link
              per row, and validated on every run.
            </li>
            <li>
              Forecasts are published only for quarters already reported. A forward forecast
              exists behind a switch and is off.
            </li>
          </ul>
        </section>

        <section className="writeup-section" aria-labelledby="w-stack">
          <h2 id="w-stack">Built with</h2>
          <p>
            Python, SQL in DuckDB, the OpenAI API with structured outputs, React and TypeScript with
            D3 scales, and GitHub Actions for tests, data refreshes, and deploys. Designed and built
            by Jacob Kambour, MS Finance &amp; Analytics, Santa Clara University.
          </p>
          <p>
            <a className="writeup-cta" href={DASHBOARD_HREF}>
              Open the dashboard
            </a>
          </p>
        </section>
      </main>
      <footer className="colophon">
        <div className="canvas">
          <p className="disclaimer">{footerDisclaimer}</p>
        </div>
      </footer>
    </>
  );
}
