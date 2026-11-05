import type { SectionProps } from "./types";
import {
  accuracyMetrics,
  backtestQuarters,
  barFillPercent,
  formatErrorPercent,
  quarterLabel,
} from "./AccuracyFormat";
import "./AccuracySection.css";

type ErrorCellProps = { value: number | null | undefined };

/** One error value: a quiet inline bar capped at 100%, then the full number. */
function ErrorCell({ value }: ErrorCellProps) {
  const text = formatErrorPercent(value);
  if (value === null || value === undefined || text === null) {
    return (
      <td className="acc-cell">
        <span aria-hidden="true">—</span>
        <span className="visually-hidden">not available</span>
      </td>
    );
  }
  const over = value > 100;
  return (
    <td className="acc-cell">
      <span className="acc-meter">
        <span className="acc-bar" aria-hidden="true">
          <span className="acc-fill" style={{ width: `${barFillPercent(value)}%` }} />
        </span>
        {over ? (
          <span className="acc-over" aria-hidden="true">
            +
          </span>
        ) : null}
        <span className="acc-value">{text}</span>
      </span>
    </td>
  );
}

/** Model accuracy: absolute percent error of the base forecast, by quarter and metric. */
export function AccuracySection({ dashboard, quarter }: SectionProps) {
  const rows = dashboard.backtest.rows;
  const averages = dashboard.backtest.averages;
  const quarters = backtestQuarters(rows);
  const byKey = new Map(rows.map((row) => [`${row.quarter}|${row.metric}`, row.abs_pct_error]));

  return (
    <>
      <hr className="ledger" />
      <section className="accuracy" aria-labelledby="accuracy-heading">
        <h2 id="accuracy-heading">Model accuracy</h2>
        <p className="accuracy-intro">
          Absolute percent error of the base forecast against first-reported actuals, for each published
          quarter. Large misses stay in the table.
        </p>

        {rows.length === 0 ? (
          <p className="acc-empty">No backtest yet: the model needs published quarters with forecasts.</p>
        ) : (
          <div className="acc-scroll">
            <table className="acc-table">
              <caption className="visually-hidden">Absolute percent error by quarter</caption>
              <thead>
                <tr>
                  <th scope="col" className="acc-first">
                    Quarter
                  </th>
                  {accuracyMetrics.map((metric) => (
                    <th scope="col" key={metric.key}>
                      {metric.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {quarters.map((id) => {
                  const selected = id === quarter.quarter;
                  return (
                    <tr key={id} className={selected ? "acc-selected" : undefined}>
                      <th scope="row" className="acc-first">
                        {selected ? (
                          <>
                            <span className="visually-hidden">Selected quarter</span>{" "}
                          </>
                        ) : null}
                        {quarterLabel(id)}
                      </th>
                      {accuracyMetrics.map((metric) => (
                        <ErrorCell key={metric.key} value={byKey.get(`${id}|${metric.key}`)} />
                      ))}
                    </tr>
                  );
                })}
                <tr className="acc-average">
                  <th scope="row" className="acc-first">
                    Average
                  </th>
                  {accuracyMetrics.map((metric) => (
                    <ErrorCell key={metric.key} value={averages[metric.key]} />
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
