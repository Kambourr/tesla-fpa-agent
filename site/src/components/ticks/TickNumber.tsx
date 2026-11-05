import { useId, useState, type KeyboardEvent, type ReactNode } from "react";
import type { ClaimStatus, ClaimView } from "../../data/types";
import {
  formatClaimValue,
  formatExpected,
  metricLabel,
  periodLabel,
} from "./tickFormat";
import "./ticks.css";

export type TickNumberProps = {
  /** The number as written in the prose, for example "$28.05B". */
  text: string;
  claim: ClaimView;
  /** Shown as the period when the claim's period is not a quarter id. */
  quarterLabel?: string;
};

/** The hand-drawn-style mark for each status. Color comes from ticks.css. */
export function TickIcon({ status }: { status: ClaimStatus }) {
  if (status === "verified") {
    return (
      <svg className="tick-icon tick-icon-verified" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
        <path d="M2 9.1C3.2 9.7 4.4 11.3 5.8 13.3C8 9.2 10.8 5.6 14 2.7" />
      </svg>
    );
  }
  if (status === "flagged") {
    return (
      <svg className="tick-icon tick-icon-flagged" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
        <path className="tick-pole" d="M3.2 14.2V1.8" />
        <path className="tick-flag" d="M3.2 2.4H12.6L10.2 5.6L12.6 8.8H3.2Z" />
      </svg>
    );
  }
  return (
    <svg className="tick-icon tick-icon-unsupported" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <circle className="tick-ring" cx="8" cy="8" r="6.4" />
      <path className="tick-query" d="M5.9 6.1C5.9 4.8 6.8 4 8 4C9.2 4 10.1 4.7 10.1 5.9C10.1 7.4 8 7.6 8 9.1" />
      <circle className="tick-dot" cx="8" cy="11.9" r="0.9" />
    </svg>
  );
}

function lowerFirst(text: string): string {
  return text.charAt(0).toLowerCase() + text.slice(1);
}

/** The accessible name for the tick, which is also what a screen reader announces on focus. */
function tickName(claim: ClaimView, claimedValue: string, expectedValue: string | null): string {
  if (claim.status === "verified") {
    return `Verified: ties to ${claim.source ?? "the data"}, ${lowerFirst(metricLabel(claim.metric))} ${claimedValue}`;
  }
  if (claim.status === "flagged") {
    return expectedValue
      ? `Flagged: the filing shows ${expectedValue}`
      : "Flagged: does not match the data";
  }
  return "Unsupported: this figure could not be traced to the data";
}

function periodText(claim: ClaimView, quarterLabel: string | undefined): string {
  return periodLabel(claim.period) ?? quarterLabel ?? claim.period;
}

/**
 * A figure from the AI-written text, followed by its tick. Verified ticks open the
 * source filing (a link when source_url exists). Flagged and unsupported ticks show
 * a tooltip only. Hover and keyboard focus open the tooltip; Escape closes it.
 */
export function TickNumber({ text, claim, quarterLabel }: TickNumberProps) {
  const tooltipId = useId();
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const open = (hovered || focused) && !dismissed;

  const claimedValue = formatClaimValue(claim.value, claim.unit);
  const expectedValue =
    claim.expected === null ? null : formatExpected(claim.expected, claim.expected_unit);
  const name = tickName(claim, claimedValue, expectedValue);
  const label = metricLabel(claim.metric);

  let result: string;
  if (claim.status === "verified") {
    result = `Ties to the filing at ${claimedValue}`;
  } else if (claim.status === "flagged") {
    result = `Text says ${claimedValue}, which does not match`;
  } else {
    result = "Could not be traced to the data";
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLSpanElement>) => {
    if (event.key === "Escape") setDismissed(true);
  };

  const onMouseEnter = () => {
    setHovered(true);
    setDismissed(false);
  };
  const onFocus = () => {
    setFocused(true);
    setDismissed(false);
  };

  const triggerProps = {
    className: "tick-trigger",
    "aria-label": name,
    "aria-describedby": tooltipId,
    onFocus,
    onBlur: () => setFocused(false),
  };

  let trigger: ReactNode;
  if (claim.status === "verified" && claim.source_url) {
    trigger = (
      <a href={claim.source_url} target="_blank" rel="noopener noreferrer" {...triggerProps}>
        <TickIcon status={claim.status} />
      </a>
    );
  } else {
    trigger = (
      <button type="button" {...triggerProps}>
        <TickIcon status={claim.status} />
      </button>
    );
  }

  return (
    <span
      className="tick-number"
      data-status={claim.status}
      onMouseEnter={onMouseEnter}
      onMouseLeave={() => setHovered(false)}
      onKeyDown={handleKeyDown}
    >
      <span className={claim.status === "flagged" ? "tick-text is-flagged" : "tick-text"}>{text}</span>
      {trigger}
      <span id={tooltipId} role="tooltip" className="tick-tooltip" hidden={!open}>
        <span className="tick-tooltip-title">{label}</span>
        <span className="tick-tooltip-row">
          <span className="tick-tooltip-key">Period</span>
          <span className="tick-tooltip-value">{periodText(claim, quarterLabel)}</span>
        </span>
        <span className="tick-tooltip-row">
          <span className="tick-tooltip-key">Source</span>
          <span className="tick-tooltip-value">{claim.source ?? "None given"}</span>
        </span>
        <span className="tick-tooltip-row">
          <span className="tick-tooltip-key">Result</span>
          <span className="tick-tooltip-value">{result}</span>
        </span>
        {claim.status === "flagged" && (
          <span className="tick-tooltip-row">
            <span className="tick-tooltip-key">Filing shows</span>
            <span className="tick-tooltip-value">{expectedValue ?? "No value found"}</span>
          </span>
        )}
      </span>
    </span>
  );
}
