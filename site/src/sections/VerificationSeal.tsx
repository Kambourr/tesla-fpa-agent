import type { CSSProperties } from "react";
import "./VerificationSeal.css";
import type { QaSet, QuarterView } from "../data/types";
import { TickIcon } from "../components/ticks/TickNumber";
import {
  METHOD_ANCHOR,
  commentaryCounts,
  hasOpenFigures,
  sealSentence,
  sealTickCount,
} from "./VerificationSealFormat";

export type VerificationSealProps = {
  quarter: QuarterView;
  /** The Q&A set. It counts only when its quarter is the selected one. */
  qa: QaSet | null;
  /** True once the hero waterfall has finished drawing. The ticks appear after this. */
  drawn: boolean;
};

const NO_COMMENTARY = "The commentary has not been written yet, so no figures are checked for this quarter.";

/** Verification seal under the hero bridge: the verified count, its ticks, and a link to the methods section. */
export function VerificationSeal({ quarter, qa, drawn }: VerificationSealProps) {
  const counts = commentaryCounts(quarter, qa);
  const dataDrawn = drawn ? "true" : undefined;

  if (!counts) {
    return (
      <div className="verification-seal" data-drawn={dataDrawn}>
        <p className="seal-text">{NO_COMMENTARY}</p>
        <SealLink />
      </div>
    );
  }

  const ticks = sealTickCount(counts);
  const flagIndex = ticks;
  return (
    <div className="verification-seal" data-drawn={dataDrawn}>
      <p className="seal-text">
        {sealSentence(counts)}
        <span className="seal-marks" aria-hidden="true">
          {Array.from({ length: ticks }, (_, index) => (
            <span
              key={`tick-${index}`}
              className="seal-mark"
              style={{ "--seal-index": index } as CSSProperties}
            >
              <TickIcon status="verified" />
            </span>
          ))}
          {hasOpenFigures(counts) ? (
            <span className="seal-mark seal-flag" style={{ "--seal-index": flagIndex } as CSSProperties}>
              <TickIcon status="flagged" />
            </span>
          ) : null}
        </span>
      </p>
      <SealLink />
    </div>
  );
}

function SealLink() {
  return (
    <p className="seal-link-line">
      <a className="seal-link" href={METHOD_ANCHOR}>
        See how the figures are checked
      </a>
    </p>
  );
}
