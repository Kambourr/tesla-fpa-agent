import { useId } from "react";
import { TickIcon } from "./TickNumber";
import "./ticks.css";

const ENTRIES = [
  { status: "verified", text: "Ties to the filing or computed table" },
  { status: "flagged", text: "Flagged: does not match" },
  { status: "unsupported", text: "Unsupported: could not be traced" },
] as const;

/** An auditor's tickmark legend: the three marks and what each one means. */
export function TickLegend() {
  const titleId = useId();
  return (
    <section className="tick-legend" aria-labelledby={titleId}>
      <h3 id={titleId} className="tick-legend-title">
        Tickmark legend
      </h3>
      <dl className="tick-legend-list">
        {ENTRIES.map((entry) => (
          <div className="tick-legend-item" key={entry.status}>
            <dt>
              <TickIcon status={entry.status} />
            </dt>
            <dd>{entry.text}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
