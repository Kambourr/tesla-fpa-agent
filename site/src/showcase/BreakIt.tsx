import { useMemo, useState } from "react";
import { TickIcon } from "../components/ticks/TickNumber";
import { formatClaimValue, formatExpected, metricLabel, periodLabel } from "../components/ticks/tickFormat";
import type { Dashboard, QuarterView } from "../data/types";
import { commentaryTotals } from "../sections/heroModel";
import { FirstDraftLine } from "./Pipeline";
import { buildExcerpt, checkEdit, editedValueText, ruleText, unitChoices, type Figure } from "./breakItModel";
import "./BreakIt.css";

const UNIT_LABEL: Record<string, string> = {
  "USD billion": "billion",
  "USD million": "million",
  "USD thousand": "thousand",
  USD: "dollars",
  percent: "percent",
  "percentage points": "percentage points",
  "thousand units": "thousand",
  units: "units",
};

/** A figure about 3% off, written with the same decimals: something to try. */
export function nudged(number: string): string {
  const plain = number.replace(/,/g, "");
  const decimals = plain.includes(".") ? plain.split(".")[1].length : 0;
  return (Number(plain) * 1.03).toFixed(decimals);
}

/** " Off by 3.4%." for dollar figures, " Off by 0.4 points." for percentages. */
export function missText(normalized: number | null, expected: number, unit: string | null): string {
  if (normalized === null || normalized === expected) return "";
  if (unit === "percent") return ` Off by ${Math.abs(normalized - expected).toFixed(2)} points.`;
  if (expected === 0) return "";
  const pct = (Math.abs(normalized - expected) / Math.abs(expected)) * 100;
  if (pct < 0.01) return "";
  return ` Off by ${pct >= 100 ? Math.round(pct).toLocaleString("en-US") : pct.toFixed(pct < 1 ? 2 : 1)}%.`;
}

function unitLabel(unit: string): string {
  return UNIT_LABEL[unit] ?? unit;
}

/**
 * "Try to break it": the model's memo with every figure editable. Each edit is
 * checked in the browser with the pipeline's verifier rules against the value
 * the code published for that claim. No model call, no network.
 */
export function BreakIt({ dashboard, quarter }: { dashboard: Dashboard; quarter: QuarterView }) {
  const excerpt = useMemo(() => buildExcerpt(quarter), [quarter]);
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [units, setUnits] = useState<Record<string, string>>({});
  const [selectedId, setSelectedId] = useState("f0");

  if (!excerpt) {
    return (
      <section className="breakit" aria-labelledby="breakit-title">
        <h2 id="breakit-title" className="breakit-title">
          Try to break it
        </h2>
        <p className="breakit-empty">
          The model's memo for {quarter.label} has not been written yet, so there is nothing to
          test. Pick another quarter.
        </p>
      </section>
    );
  }

  const typedFor = (figure: Figure) => edits[figure.id] ?? figure.number;
  const unitFor = (figure: Figure) => units[figure.id] ?? figure.claim.unit;
  const resultFor = (figure: Figure) => checkEdit(figure, typedFor(figure), unitFor(figure));
  const selected = excerpt.figures.find((figure) => figure.id === selectedId) ?? excerpt.figures[0];
  const result = resultFor(selected);
  const changed = Object.keys(edits).length > 0 || Object.keys(units).length > 0;
  const writtenText = editedValueText(selected, typedFor(selected));
  const writtenNumber = Number(writtenText);
  const period = periodLabel(selected.claim.period) ?? quarter.label;

  return (
    <section className="breakit" aria-labelledby="breakit-title">
      <div className="breakit-head">
        <p className="breakit-kicker">Try to break it</p>
        <h2 id="breakit-title" className="breakit-title">
          Change a number the model wrote. Code checks it against the filing.
        </h2>
      </div>

      <div className="breakit-body">
        <div className="breakit-left">
        <blockquote className="breakit-memo" aria-label={`The model's memo for ${quarter.label}, with editable figures`}>
          {excerpt.pieces.map((piece, index) => {
            if (piece.kind === "text") return <span key={index}>{piece.text}</span>;
            const figure = piece.figure;
            const status = resultFor(figure).status;
            const typed = typedFor(figure);
            const unitChanged = unitFor(figure) !== figure.claim.unit;
            return (
              <span
                key={index}
                className={`breakit-figure breakit-figure-${status}${figure.id === selected.id ? " is-selected" : ""}`}
              >
                {figure.prefix}
                <input
                  className="breakit-input"
                  value={typed}
                  inputMode="decimal"
                  spellCheck={false}
                  autoComplete="off"
                  style={{ width: `${Math.max(typed.length, 2) * 0.56 + 0.3}em` }}
                  aria-label={`${metricLabel(figure.claim.metric)}, ${periodLabel(figure.claim.period) ?? quarter.label}. Edit to test the checker.`}
                  aria-describedby="breakit-result"
                  onFocus={() => setSelectedId(figure.id)}
                  onChange={(event) => {
                    setSelectedId(figure.id);
                    setEdits((current) => ({ ...current, [figure.id]: event.target.value }));
                  }}
                />
                {unitChanged ? ` ${unitLabel(unitFor(figure))}` : figure.suffix}
                <TickIcon status={status} />
              </span>
            );
          })}
        </blockquote>
        <Totals dashboard={dashboard} />
        </div>

        <div className="breakit-inspector" aria-label="What the code checked">
          <p className="breakit-metric">
            {metricLabel(selected.claim.metric)} <span>· {period}</span>
          </p>
          <dl className="breakit-facts">
            <div>
              <dt>Written</dt>
              <dd>
                {Number.isFinite(writtenNumber)
                  ? formatClaimValue(writtenNumber, unitFor(selected))
                  : typedFor(selected) || "nothing"}
              </dd>
            </div>
            <div>
              <dt>{selected.claim.source_url ? "Filing" : "Computed"}</dt>
              <dd>{formatExpected(selected.claim.expected as number, selected.claim.expected_unit)}</dd>
            </div>
          </dl>
          <label className="breakit-unit">
            <span>Unit</span>
            <select
              value={unitFor(selected)}
              onChange={(event) => setUnits((current) => ({ ...current, [selected.id]: event.target.value }))}
            >
              {unitChoices(selected.claim).map((unit) => (
                <option key={unit} value={unit}>
                  {unitLabel(unit)}
                </option>
              ))}
            </select>
          </label>
          <p className="breakit-rule">{ruleText(selected.claim.expected_unit)}</p>
          <p id="breakit-result" className={`breakit-result breakit-result-${result.status}`} aria-live="polite">
            <TickIcon status={result.status} />
            <span>
              <strong>{result.status === "verified" ? "Ties." : "Flagged."}</strong> {result.reason}
              {missText(result.normalized, selected.claim.expected as number, selected.claim.expected_unit)}
            </span>
          </p>
          <p className="breakit-source">
            {selected.claim.source_url ? (
              <a href={selected.claim.source_url} target="_blank" rel="noreferrer">
                {selected.claim.source}
              </a>
            ) : (
              <span>{selected.claim.source}</span>
            )}
          </p>
          {changed ? (
            <button
              type="button"
              className="breakit-reset"
              onClick={() => {
                setEdits({});
                setUnits({});
              }}
            >
              Restore the model's figures
            </button>
          ) : (
            <p className="breakit-hint">
              Try {nudged(selected.number)} instead of {selected.number}, or change the unit.
            </p>
          )}
        </div>
      </div>
      <p className="breakit-note">
        These are the pipeline verifier's rules running in your browser, tested case for case against
        the Python version. No model is called.
      </p>
    </section>
  );
}

function Totals({ dashboard }: { dashboard: Dashboard }) {
  const totals = commentaryTotals(dashboard);
  const missed = totals.flagged + totals.unsupported;
  return (
    <div className="breakit-totals">
      <p>
        <strong>
          {totals.verified.toLocaleString("en-US")} of {totals.total.toLocaleString("en-US")}
        </strong>{" "}
        figures the model wrote across this site tie to the filings
        {missed > 0 ? `; ${missed} are shown flagged` : ""}.
      </p>
      <FirstDraftLine dashboard={dashboard} />
    </div>
  );
}
