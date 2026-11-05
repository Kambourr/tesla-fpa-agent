import { useState } from "react";
import type { Scenario } from "../data/types";
import type { SectionProps } from "./types";
import {
  buildForecastRows,
  flexSentence,
  formatAmount,
  formatVariance,
  formatVariancePercent,
  type ForecastRow,
  varianceWord,
} from "./ForecastSectionFormat";
import "./ForecastSection.css";

const OPTIONS: { value: Scenario; label: string }[] = [
  { value: "bear", label: "Bear" },
  { value: "base", label: "Base" },
  { value: "bull", label: "Bull" },
];

const NOTE_ID = "forecast-scenario-note";

function varianceClass(favorable: boolean | null, moved: boolean): string {
  const tone =
    favorable === true
      ? "forecast-table__variance--favorable"
      : favorable === false
        ? "forecast-table__variance--unfavorable"
        : "";
  return ["forecast-table__num", "forecast-table__variance", tone, moved ? "forecast-table__cell--moved" : ""]
    .filter(Boolean)
    .join(" ");
}

function VarianceText({ text, favorable, variance }: { text: string; favorable: boolean | null; variance: number | null }) {
  const word = varianceWord(favorable, variance);
  return (
    <>
      {text}
      {word !== null && <span className="visually-hidden"> {word}</span>}
    </>
  );
}

function ForecastRowView({ row }: { row: ForecastRow }) {
  const moved = row.moved ? " forecast-table__cell--moved" : "";
  return (
    <tr>
      <th scope="row" className="forecast-table__line">
        {row.label}
      </th>
      <td className={`forecast-table__num${moved}`}>{formatAmount(row.forecast, row.unit)}</td>
      <td className="forecast-table__num">{formatAmount(row.actual, row.unit)}</td>
      <td className={varianceClass(row.favorable, row.moved)}>
        <VarianceText
          text={formatVariance(row.variance, row.unit)}
          favorable={row.favorable}
          variance={row.variance}
        />
      </td>
      <td className={varianceClass(row.favorable, row.moved)}>
        <VarianceText
          text={formatVariancePercent(row.variancePct)}
          favorable={row.favorable}
          variance={row.variance}
        />
      </td>
    </tr>
  );
}

export function ForecastSection({ dashboard, quarter }: SectionProps) {
  const [chosen, setChosen] = useState<Scenario>("base");
  const hasDrivers = quarter.drivers !== null;
  const scenario: Scenario = hasDrivers ? chosen : "base";
  const rows = buildForecastRows(quarter, dashboard.scenario_flex, scenario);
  const scenarioName = OPTIONS.find((option) => option.value === scenario)?.label.toLowerCase() ?? "base";

  return (
    <>
      <section className="forecast" aria-labelledby="forecast-heading">
        <h2 id="forecast-heading">Forecast and scenarios</h2>

        <div role="group" aria-label="Scenario" className="forecast__scenarios">
          {OPTIONS.map((option) => {
            const disabled = option.value !== "base" && !hasDrivers;
            return (
              <button
                key={option.value}
                type="button"
                aria-pressed={scenario === option.value}
                aria-describedby={disabled ? NOTE_ID : undefined}
                disabled={disabled}
                onClick={() => setChosen(option.value)}
              >
                {option.label}
              </button>
            );
          })}
        </div>
        {!hasDrivers && (
          <p className="forecast__note" id={NOTE_ID}>
            Scenarios need a base forecast for this quarter.
          </p>
        )}

        <div className="forecast__table-wrap">
          <table className="forecast-table">
            <caption className="visually-hidden">
              {`${quarter.label} forecast and actual, ${scenarioName} scenario`}
            </caption>
            <thead>
              <tr>
                <th scope="col" className="forecast-table__line">
                  Line
                </th>
                <th scope="col" className="forecast-table__num">
                  Forecast
                </th>
                <th scope="col" className="forecast-table__num">
                  Actual
                </th>
                <th scope="col" className="forecast-table__num">
                  Variance $
                </th>
                <th scope="col" className="forecast-table__num">
                  Variance %
                </th>
              </tr>
            </thead>
            <tbody key={`${quarter.quarter}-${scenario}`}>
              {rows.map((row) => (
                <ForecastRowView key={row.metric} row={row} />
              ))}
            </tbody>
          </table>
        </div>

        <p className="forecast__flex">{flexSentence(dashboard.scenario_flex)}</p>
      </section>
    </>
  );
}
