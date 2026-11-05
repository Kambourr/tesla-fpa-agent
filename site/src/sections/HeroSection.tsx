import { useEffect, useId, useState, type CSSProperties } from "react";
import { scaleBand, scaleLinear } from "d3-scale";
import "./HeroSection.css";
import type { SectionProps } from "./types";
import { VerificationSeal } from "./VerificationSeal";
import {
  buildRevenueBridge,
  formatAxisUsd,
  formatBridgeLede,
  formatSignedUsd,
  formatUsd,
  type BridgeStep,
  type RevenueBridgeModel,
} from "./HeroSectionFormat";

/**
 * Total draw time for the bridge. Eight bars draw in order, each starting 0.12 s after the
 * last (the delay lives in HeroSection.css, from --bar-index).
 */
const DRAW_MS = 1200;
const BAR_MIN_HEIGHT = 2;

const WIDTH = 800;
const HEIGHT = 400;
const MARGIN = { top: 44, right: 8, bottom: 84, left: 64 };
const LABEL_CHARS = 11;

const EMPTY_MESSAGE = "No revenue bridge for this quarter: the forecast or an actual revenue line is missing.";

function prefersReducedMotion(): boolean {
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return false;
  }
}

/** Splits a category label into at most three lines of about `maxChars` characters. */
function wrapLabel(text: string, maxChars: number, maxLines = 3): string[] {
  const words = text.split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let current = "";
  for (const word of words) {
    const next = current ? `${current} ${word}` : word;
    if (current && next.length > maxChars) {
      lines.push(current);
      current = word;
    } else {
      current = next;
    }
  }
  if (current) {
    lines.push(current);
  }
  if (lines.length > maxLines) {
    return [...lines.slice(0, maxLines - 1), lines.slice(maxLines - 1).join(" ")];
  }
  return lines;
}

function barClass(step: BridgeStep): string {
  if (step.kind === "total") {
    return step.key === "forecast" ? "hero-bar is-forecast" : "hero-bar is-actual";
  }
  return step.favorable ? "hero-bar is-favorable" : "hero-bar is-unfavorable";
}

function summaryLabel(model: RevenueBridgeModel): string {
  const drivers = model.steps
    .filter((step) => step.kind === "driver")
    .map((step) => `${step.label} ${formatSignedUsd(step.value)}, ${step.favorable ? "favorable" : "unfavorable"}`)
    .join("; ");
  return `Revenue bridge for ${model.label}. Forecast ${formatUsd(model.forecast)}, actual ${formatUsd(model.actual)}. ${drivers}.`;
}

export function HeroSection({ dashboard, quarter }: SectionProps) {
  const headingId = useId();
  const model = buildRevenueBridge(quarter);
  const hasChart = model !== null;
  const [drawn, setDrawn] = useState<boolean>(() => prefersReducedMotion());

  useEffect(() => {
    if (drawn || !hasChart) {
      return;
    }
    const timer = window.setTimeout(() => setDrawn(true), DRAW_MS);
    return () => window.clearTimeout(timer);
  }, [drawn, hasChart]);

  if (!model) {
    return (
      <section className="empty" aria-labelledby={headingId} data-drawn="true">
        <h2 id={headingId} className="visually-hidden">
          Revenue bridge, forecast to actual
        </h2>
        <p>{EMPTY_MESSAGE}</p>
      </section>
    );
  }

  // Bars animate only until the first draw finishes. Quarter switches after that never replay it.
  const animating = !drawn;
  const { steps } = model;
  const innerWidth = WIDTH - MARGIN.left - MARGIN.right;
  const innerHeight = HEIGHT - MARGIN.top - MARGIN.bottom;

  // The axis starts just below the lowest point the bridge reaches, not at zero:
  // from zero, a $10M driver on a $30B bridge is invisible. The two total bars
  // are cut at the bottom with a break mark, and a note says where the axis starts.
  const { domainMin, domainMax, truncated } = bridgeDomain(steps);
  const y = scaleLinear().domain([domainMin, domainMax]).range([innerHeight, 0]);
  const x = scaleBand<string>()
    .domain(steps.map((step) => step.key))
    .range([0, innerWidth])
    .padding(0.2);
  const bandWidth = x.bandwidth();
  const ticks = y.ticks(4);

  return (
    <section className="hero-bridge" aria-labelledby={headingId} data-drawn={drawn ? "true" : undefined}>
      <h2 id={headingId} className="visually-hidden">
        Revenue bridge, forecast to actual
      </h2>
      <p className="lede">{formatBridgeLede(model)}</p>

      <div className="hero-bridge-scroll">
        <svg
          className="hero-bridge-svg"
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          role="img"
          aria-label={summaryLabel(model)}
        >
          <g transform={`translate(${MARGIN.left} ${MARGIN.top})`}>
            {ticks.map((tick) => (
              <g key={`tick-${tick}`} className="hero-axis">
                <line className="hero-grid" x1={0} x2={innerWidth} y1={y(tick)} y2={y(tick)} />
                <text className="hero-axis-label" x={-10} y={y(tick)} dy="0.32em" textAnchor="end">
                  {formatAxisUsd(tick)}
                </text>
              </g>
            ))}

            {steps.slice(0, -1).map((step, index) => {
              const next = steps[index + 1];
              const level = y(step.end);
              return (
                <line
                  key={`connector-${step.key}`}
                  className="hero-connector"
                  x1={(x(step.key) ?? 0) + bandWidth}
                  x2={x(next.key) ?? 0}
                  y1={level}
                  y2={level}
                />
              );
            })}

            {steps.map((step, index) => {
              const cx = (x(step.key) ?? 0) + bandWidth / 2;
              const top = y(Math.max(step.start, step.end));
              const bottom = Math.min(innerHeight, y(Math.min(step.start, step.end)));
              const height = Math.max(BAR_MIN_HEIGHT, bottom - top);
              const glyph = step.kind === "driver" && step.value !== 0 ? (step.value > 0 ? "▲" : "▼") : null;
              const glyphClass = step.favorable ? "is-favorable" : "is-unfavorable";
              const valueText = step.kind === "total" ? formatUsd(step.value) : formatSignedUsd(step.value);
              const labelLines = wrapLabel(step.label, LABEL_CHARS);
              return (
                <g
                  key={step.key}
                  className={animating ? "hero-step is-drawing" : "hero-step"}
                  data-kind={step.kind}
                  style={{ "--bar-index": index } as CSSProperties}
                >
                  <rect
                    className={barClass(step)}
                    x={x(step.key) ?? 0}
                    y={top}
                    width={bandWidth}
                    height={height}
                  />
                  {truncated && step.kind === "total" ? (
                    <path
                      className="hero-break"
                      d={`M ${(x(step.key) ?? 0) - 3} ${innerHeight - 14} l ${bandWidth + 6} -8 M ${(x(step.key) ?? 0) - 3} ${innerHeight - 6} l ${bandWidth + 6} -8`}
                    />
                  ) : null}
                  <text className="hero-value" x={cx} y={top - 9} textAnchor="middle">
                    {glyph ? (
                      <tspan className={`hero-glyph ${glyphClass}`}>{glyph} </tspan>
                    ) : null}
                    {valueText}
                  </text>
                  <text className="hero-category" x={cx} y={innerHeight + 20} textAnchor="middle">
                    {labelLines.map((line, lineIndex) => (
                      <tspan key={`${step.key}-${lineIndex}`} x={cx} dy={lineIndex === 0 ? 0 : 15}>
                        {line}
                      </tspan>
                    ))}
                  </text>
                </g>
              );
            })}

            <line className="hero-baseline" x1={0} x2={innerWidth} y1={innerHeight} y2={innerHeight} />
          </g>
        </svg>
      </div>
      {truncated ? (
        <p className="hero-axis-note">
          The axis starts at {formatAxisUsd(domainMin)}, not zero, so the drivers are visible. The
          forecast and actual bars are cut at the bottom.
        </p>
      ) : null}

      <div className="hero-table-clip">
        <table className="visually-hidden">
          <caption>Revenue bridge for {model.label}</caption>
          <thead>
            <tr>
              <th scope="col">Step</th>
              <th scope="col">Amount</th>
              <th scope="col">Direction</th>
            </tr>
          </thead>
          <tbody>
            {steps.map((step) => (
              <tr key={step.key}>
                <th scope="row">{step.label}</th>
                <td>{step.kind === "total" ? formatUsd(step.value) : formatSignedUsd(step.value)}</td>
                <td>{step.kind === "total" ? "Total" : step.favorable ? "favorable" : "unfavorable"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <VerificationSeal quarter={quarter} qa={dashboard.qa} drawn={drawn} />
    </section>
  );
}

/** Axis range for the bridge: a padded window around the levels, or from zero if it reaches there. */
export function bridgeDomain(steps: readonly { start: number; end: number }[]): {
  domainMin: number;
  domainMax: number;
  truncated: boolean;
} {
  const levels = steps.flatMap((step) => [step.start, step.end]).filter((level) => level !== 0);
  const low = Math.min(...levels);
  const high = Math.max(...levels);
  const span = high - low || Math.abs(high) * 0.05 || 1;
  const step = niceStep(span / 3);
  const paddedMin = Math.floor((low - span * 0.5) / step) * step;
  const domainMax = Math.ceil((high + span * 0.12) / step) * step;
  if (paddedMin <= 0 || low <= 0) {
    return { domainMin: Math.min(0, Math.floor(low / step) * step), domainMax, truncated: false };
  }
  return { domainMin: paddedMin, domainMax, truncated: true };
}

function niceStep(raw: number): number {
  const power = 10 ** Math.floor(Math.log10(raw));
  const unit = raw / power;
  const nice = unit <= 1 ? 1 : unit <= 2 ? 2 : unit <= 5 ? 5 : 10;
  return nice * power;
}
