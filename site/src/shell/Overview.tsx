import type { Dashboard, QuarterView } from "../data/types";
import { commentaryTotals } from "../sections/heroModel";
import { formatCost, formatRunTime } from "../sections/AgentRunFormat";
import {
  buildRevenueBridge,
  formatSignedPercent,
  formatSignedUsd,
  formatUsd,
} from "../sections/HeroSectionFormat";
import { HeroSection } from "../sections/HeroSection";
import "./Overview.css";

export const OVERVIEW_HEADLINE =
  "An agent that reads Tesla's public filings, forecasts the quarter, explains the miss, and writes the memo.";

type Props = {
  dashboard: Dashboard;
  quarter: QuarterView;
  onSelectQuarter: (id: string) => void;
};

function count(value: number): string {
  return value.toLocaleString("en-US");
}

export function proofChips(dashboard: Dashboard): string[] {
  const chips: string[] = [];
  const sources = dashboard.sources;
  if (sources) {
    chips.push(`${count(sources.facts)} facts`);
    chips.push(`${count(sources.filings)} filings`);
  }
  const totals = commentaryTotals(dashboard);
  if (totals.total > 0) {
    const allTied =
      totals.verified === totals.total && totals.flagged === 0 && totals.unsupported === 0;
    chips.push(allTied ? "Every figure checked" : `${count(totals.verified)} of ${count(totals.total)} figures checked`);
  }
  const full = dashboard.last_full_run;
  const time = full ? formatRunTime(full.duration_seconds) : null;
  const cost = full ? formatCost(full.estimated_cost_usd) : null;
  if (time && cost) {
    chips.push(`Full run ${time}, ${cost}`);
  } else if (time) {
    chips.push(`Full run ${time}`);
  }
  return chips;
}

export function Overview({ dashboard, quarter, onSelectQuarter }: Props) {
  const model = buildRevenueBridge(quarter);
  const chips = proofChips(dashboard);
  const varianceWord =
    model === null || model.variance === 0
      ? null
      : model.variance > 0
        ? "favorable"
        : "unfavorable";

  return (
    <div className="overview">
      <h1 className="overview-title">{OVERVIEW_HEADLINE}</h1>
      {model ? (
        <ul className="kpis">
          <li>
            <p className="kpi-label">Actual revenue</p>
            <p className="kpi-value">{formatUsd(model.actual)}</p>
          </li>
          <li>
            <p className="kpi-label">Forecast</p>
            <p className="kpi-value">{formatUsd(model.forecast)}</p>
          </li>
          <li>
            <p className="kpi-label">Variance</p>
            <p className="kpi-value">{formatSignedUsd(model.variance)}</p>
            <p className="kpi-sub">
              {model.variancePct === null ? null : `${formatSignedPercent(model.variancePct)} `}
              {varianceWord}
            </p>
          </li>
        </ul>
      ) : null}
      <HeroSection
        dashboard={dashboard}
        quarter={quarter}
        onSelectQuarter={onSelectQuarter}
        variant="chart"
      />
      {chips.length > 0 ? (
        <ul className="proof">
          {chips.map((chip) => (
            <li key={chip}>{chip}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
