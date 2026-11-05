import { useId, useState } from "react";
import { NarrativeText } from "../components/ticks/NarrativeText";
import type { QaAnswer } from "../data/types";
import { answersQuarterLabel, firstSourcedClaim, isOtherQuarter, usesAllQuarters } from "./AskFormat";
import type { SectionProps } from "./types";
import "./AskSection.css";

type AnswerItemProps = {
  answer: QaAnswer;
  open: boolean;
  idBase: string;
  onToggle: (number: number) => void;
};

/** One question: a disclosure button, and a panel with the answer, its ticks and a source line. */
function AnswerItem({ answer, open, idBase, onToggle }: AnswerItemProps) {
  const buttonId = `${idBase}-question-${answer.number}`;
  const panelId = `${idBase}-answer-${answer.number}`;
  const source = firstSourcedClaim(answer.claims);

  return (
    <li className={open ? "ask-item is-open" : "ask-item"}>
      <button
        type="button"
        id={buttonId}
        className="ask-question"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => onToggle(answer.number)}
      >
        <span className="ask-number">{answer.number}.</span>{" "}
        <span className="ask-text">{answer.question}</span>
        {usesAllQuarters(answer.number) ? <span className="ask-tag">Uses all 12 quarters</span> : null}
        <span className="ask-indicator" aria-hidden="true">
          {open ? "−" : "+"}
        </span>
      </button>
      <div id={panelId} className="ask-panel">
        <div className="ask-panel-inner">
          <div className="ask-body">
            <NarrativeText className="ask-answer" text={answer.text} claims={answer.claims} />
            {source ? (
              <p className="ask-source">
                Source:{" "}
                <a href={source.source_url ?? undefined} target="_blank" rel="noopener noreferrer">
                  {source.source ?? source.source_url}
                </a>
              </p>
            ) : null}
          </div>
        </div>
      </div>
    </li>
  );
}

/** Ask the analyst: pre-answered questions from the published JSON. Visitors do not call the model. */
export function AskSection({ dashboard, quarter, onSelectQuarter }: SectionProps) {
  const idBase = useId();
  const [openNumbers, setOpenNumbers] = useState<number[]>([]);
  const qa = dashboard.qa;

  const toggle = (number: number) => {
    setOpenNumbers((current) =>
      current.includes(number) ? current.filter((item) => item !== number) : [...current, number],
    );
  };

  return (
    <>
      <hr className="ledger" />
      <section className="ask" aria-labelledby="ask-heading">
        <h2 id="ask-heading">Ask the analyst</h2>
        <p className="ask-intro">
          Ten questions, answered by the pipeline's model from the computed tables and checked by code. Visitors do
          not call the model.
        </p>

        {qa === null ? (
          <p className="ask-empty">
            The answers have not been written yet. They appear after the next full pipeline run, each checked against
            the filings.
          </p>
        ) : (
          <>
            {isOtherQuarter(quarter, qa.quarter) ? (
              <div className="ask-note">
                <p>These answers cover {answersQuarterLabel(dashboard, qa.quarter)} only.</p>
                <button type="button" className="ask-switch" onClick={() => onSelectQuarter(qa.quarter)}>
                  Show {answersQuarterLabel(dashboard, qa.quarter)}
                </button>
              </div>
            ) : null}
            <ul className="ask-list">
              {qa.answers.map((answer) => (
                <AnswerItem
                  key={answer.number}
                  answer={answer}
                  open={openNumbers.includes(answer.number)}
                  idBase={idBase}
                  onToggle={toggle}
                />
              ))}
            </ul>
          </>
        )}
      </section>
    </>
  );
}
