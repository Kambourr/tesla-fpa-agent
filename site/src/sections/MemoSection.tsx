import { NarrativeText } from "../components/ticks/NarrativeText";
import { TickLegend } from "../components/ticks/TickLegend";
import type { VerificationCounts } from "../data/types";
import type { SectionProps } from "./types";
import "./MemoSection.css";

/** The analyst memo as a sheet of paper, with the tickmark legend beside it on wide screens. */
export function MemoSection({ quarter }: SectionProps) {
  const memo = quarter.memo;

  return (
    <>
      <hr className="ledger" />
      <section className="memo-section" aria-labelledby="analyst-memo-title">
        <h2 id="analyst-memo-title">Analyst memo</h2>

        <div className="memo-layout">
          {memo ? (
            <div className="memo-sheet">
              <div className="memo-head">
                <p>To: Readers of this page</p>
                <p>Re: {quarter.label} revenue and profit against the forecast</p>
                <p>{"Prepared by: the pipeline's model; every figure checked by code"}</p>
              </div>
              <NarrativeText className="memo-body" text={memo.text} claims={memo.claims} />
              <CountLine counts={memo.verification} />
            </div>
          ) : (
            <p className="memo-empty">
              The memo for this quarter has not been written yet. It appears after the next full pipeline run, with
              every figure checked against the filings.
            </p>
          )}

          <aside className="memo-aside">
            <TickLegend />
          </aside>
        </div>
      </section>
    </>
  );
}

/** One line under the memo. Flagged and unsupported counts appear only when they are not zero. */
function CountLine({ counts }: { counts: VerificationCounts }) {
  return (
    <p className="memo-count">
      {`${counts.verified} of ${counts.total} figures tie to the filings.`}
      {counts.flagged > 0 ? <span className="memo-count-flagged">{` ${counts.flagged} flagged.`}</span> : null}
      {counts.unsupported > 0 ? (
        <span className="memo-count-unsupported">{` ${counts.unsupported} unsupported.`}</span>
      ) : null}
    </p>
  );
}
