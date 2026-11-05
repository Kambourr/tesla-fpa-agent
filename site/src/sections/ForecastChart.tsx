import { useEffect, useRef, useState } from "react";
import { scaleLinear, scalePoint } from "d3-scale";
import type { Dashboard } from "../data/types";
import { formatAxisBillions, formatBillions, shortQuarterLabel } from "./ForecastChartFormat";
import type { SectionProps } from "./types";
import "./ForecastChart.css";

type Series = "forecast" | "actual";

type ChartRow = {
  id: string;
  label: string;
  short: string;
  forecast: number | null;
  actual: number | null;
};

/** Below this width the chart gets a shorter plot and thins the quarter labels. */
const NARROW_WIDTH = 480;
const WIDE_HEIGHT = 360;
const NARROW_HEIGHT = 240;
const MIN_WIDTH = 280;
const FALLBACK_WIDTH = 960;

/** Total revenue for each backtest quarter, oldest first. Null stays null so the chart skips it. */
function revenueRows(dashboard: Dashboard): ChartRow[] {
  return dashboard.quarters
    .filter((quarter) => quarter.kind === "backtest")
    .map((quarter) => {
      const line = quarter.lines?.find((item) => item.metric === "total_revenue");
      return {
        id: quarter.quarter,
        label: quarter.label,
        short: shortQuarterLabel(quarter.label),
        forecast: line?.forecast ?? null,
        actual: line?.actual ?? null,
      };
    });
}

/** SVG path that breaks at each missing value instead of drawing across it. */
function linePath(
  rows: ChartRow[],
  series: Series,
  px: (id: string) => number,
  py: (value: number) => number,
): string {
  let path = "";
  let pen = false;
  for (const row of rows) {
    const value = row[series];
    if (value === null) {
      pen = false;
      continue;
    }
    path += `${pen ? "L" : "M"}${px(row.id)} ${py(value)} `;
    pen = true;
  }
  return path.trim();
}

const SERIES_NAME: Record<Series, string> = {
  forecast: "Base forecast",
  actual: "Actual",
};

export function ForecastChart({ dashboard, quarter, onSelectQuarter }: SectionProps) {
  const frameRef = useRef<HTMLDivElement>(null);
  const [frameWidth, setFrameWidth] = useState(FALLBACK_WIDTH);

  useEffect(() => {
    const frame = frameRef.current;
    if (!frame) {
      return;
    }
    const measure = () => {
      const measured = frame.clientWidth;
      if (measured > 0) {
        setFrameWidth(measured);
      }
    };
    measure();
    if (typeof ResizeObserver !== "undefined") {
      const observer = new ResizeObserver(measure);
      observer.observe(frame);
      return () => observer.disconnect();
    }
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, []);

  const rows = revenueRows(dashboard);
  const values = rows.flatMap((row) => [row.forecast, row.actual]).filter((v): v is number => v !== null);
  const hasValues = values.length > 0;

  const narrow = frameWidth <= NARROW_WIDTH;
  const width = Math.max(frameWidth, MIN_WIDTH);
  const height = narrow ? NARROW_HEIGHT : WIDE_HEIGHT;
  const margin = { top: 16, right: 16, bottom: 12, left: narrow ? 52 : 64 };
  const innerRight = width - margin.right;
  const innerBottom = height - margin.bottom;

  const x = scalePoint<string>()
    .domain(rows.map((row) => row.id))
    .range([margin.left, innerRight])
    .padding(0.5);
  const px = (id: string) => x(id) ?? margin.left;

  const maxValue = Math.max(0, ...values);
  const y = scaleLinear().domain([0, maxValue]).nice(4).range([innerBottom, margin.top]);
  const py = (value: number) => y(value);
  const ticks = y.ticks(4);
  const tickStep = ticks.length > 1 ? ticks[1] - ticks[0] : 1e9;
  const tickDecimals = tickStep < 1e9 ? 1 : 0;

  const selectedIndex = rows.findIndex((row) => row.id === quarter.quarter);
  const labelStep = narrow ? 2 : 1;
  /** On narrow screens every other label is kept, but never the selected one or its neighbours. */
  const showLabel = (index: number): boolean => {
    if (index === selectedIndex || labelStep === 1) {
      return true;
    }
    return index % labelStep === 0 && (selectedIndex < 0 || Math.abs(index - selectedIndex) > 1);
  };

  return (
    <div className="forecast-chart">
      <h3 className="forecast-chart-title">Twelve quarters, forecast against actual</h3>
      <figure className="forecast-chart-figure">
        <figcaption>Total revenue by quarter, base forecast and actual</figcaption>
        <div ref={frameRef} className="forecast-chart-frame">
          {hasValues ? (
            <svg
              className="forecast-chart-svg"
              viewBox={`0 0 ${width} ${height}`}
              aria-hidden="true"
              focusable="false"
            >
              {ticks.map((tick) => (
                <g key={tick}>
                  <line
                    className="forecast-chart-grid"
                    x1={margin.left}
                    x2={innerRight}
                    y1={py(tick)}
                    y2={py(tick)}
                  />
                  <text
                    className="forecast-chart-tick"
                    x={margin.left - 8}
                    y={py(tick)}
                    dy="0.32em"
                    textAnchor="end"
                  >
                    {formatAxisBillions(tick, tickDecimals)}
                  </text>
                </g>
              ))}
              {selectedIndex >= 0 ? (
                <line
                  className="forecast-chart-selected"
                  x1={px(quarter.quarter)}
                  x2={px(quarter.quarter)}
                  y1={margin.top}
                  y2={innerBottom}
                />
              ) : null}
              <path className="forecast-chart-line is-forecast" d={linePath(rows, "forecast", px, py)} />
              <path className="forecast-chart-line is-actual" d={linePath(rows, "actual", px, py)} />
              {rows.map((row) =>
                row.forecast === null ? null : (
                  <circle
                    key={`forecast-${row.id}`}
                    className="forecast-chart-marker is-forecast"
                    data-series="forecast"
                    data-quarter={row.id}
                    cx={px(row.id)}
                    cy={py(row.forecast)}
                    r={4.5}
                  >
                    <title>{`${SERIES_NAME.forecast}, ${row.label}: ${formatBillions(row.forecast)}`}</title>
                  </circle>
                ),
              )}
              {rows.map((row) =>
                row.actual === null ? null : (
                  <rect
                    key={`actual-${row.id}`}
                    className="forecast-chart-marker is-actual"
                    data-series="actual"
                    data-quarter={row.id}
                    x={px(row.id) - 4.5}
                    y={py(row.actual) - 4.5}
                    width={9}
                    height={9}
                  >
                    <title>{`${SERIES_NAME.actual}, ${row.label}: ${formatBillions(row.actual)}`}</title>
                  </rect>
                ),
              )}
            </svg>
          ) : (
            <p className="forecast-chart-empty">No quarter has total revenue to chart.</p>
          )}
          {hasValues ? (
            <div className="forecast-chart-xlabels">
              {rows.map((row, index) => {
                if (!showLabel(index)) {
                  return null;
                }
                const selected = row.id === quarter.quarter;
                return (
                  <button
                    key={row.id}
                    type="button"
                    className={selected ? "forecast-chart-xlabel is-selected" : "forecast-chart-xlabel"}
                    style={{ left: px(row.id) }}
                    aria-current={selected ? "true" : undefined}
                    onClick={() => onSelectQuarter(row.id)}
                  >
                    {row.short}
                    {selected ? <span className="visually-hidden"> Selected</span> : null}
                  </button>
                );
              })}
            </div>
          ) : null}
        </div>
        <ul className="forecast-chart-legend">
          <li>
            <svg className="forecast-chart-key" viewBox="0 0 36 12" aria-hidden="true" focusable="false">
              <line className="forecast-chart-line is-forecast" x1={0} x2={36} y1={6} y2={6} />
              <circle className="forecast-chart-marker is-forecast" cx={18} cy={6} r={4.5} />
            </svg>
            Base forecast
          </li>
          <li>
            <svg className="forecast-chart-key" viewBox="0 0 36 12" aria-hidden="true" focusable="false">
              <line className="forecast-chart-line is-actual" x1={0} x2={36} y1={6} y2={6} />
              <rect className="forecast-chart-marker is-actual" x={13.5} y={1.5} width={9} height={9} />
            </svg>
            Actual
          </li>
        </ul>
        <table className="visually-hidden">
          <thead>
            <tr>
              <th scope="col">Quarter</th>
              <th scope="col">Base forecast</th>
              <th scope="col">Actual</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <th scope="row">{row.label}</th>
                <td>{row.forecast === null ? "Not available" : formatBillions(row.forecast)}</td>
                <td>{row.actual === null ? "Not available" : formatBillions(row.actual)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </figure>
    </div>
  );
}
