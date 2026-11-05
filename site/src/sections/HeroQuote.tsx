import { useEffect, useRef } from "react";
import { NarrativeText } from "../components/ticks/NarrativeText";
import { commentaryTotals, heroSentence } from "./heroModel";
import type { SectionProps } from "./types";
import "./HeroQuote.css";

/**
 * The page's one memorable element: a real sentence the model wrote, set large,
 * with the code's verification tick after every figure. The ticks stamp on one
 * after another on first load; with reduced motion they are simply there.
 */
export function HeroQuote({ dashboard, quarter }: SectionProps) {
  const sentence = heroSentence(quarter);
  const totals = commentaryTotals(dashboard);
  const root = useRef<HTMLElement>(null);

  useEffect(() => {
    root.current?.querySelectorAll<HTMLElement>(".tick-number").forEach((tick, index) => {
      tick.style.setProperty("--stamp-index", String(index));
    });
  }, [sentence?.text]);

  const missed = totals.flagged + totals.unsupported;
  const checked =
    totals.total > 0
      ? `Every number checked by code: ${totals.verified.toLocaleString("en-US")} of ${totals.total.toLocaleString("en-US")} tie to the filings${missed > 0 ? `, ${missed.toLocaleString("en-US")} flagged and shown as flagged` : ""}.`
      : "Every number it writes is checked by code against the filings.";

  return (
    <figure className="hero-quote" ref={root}>
      {sentence ? (
        <blockquote>
          <NarrativeText text={sentence.text} claims={sentence.claims} />
        </blockquote>
      ) : (
        <p className="hero-quote-empty">
          The model's memo for {quarter.label} has not been written yet. It appears here after the
          next full pipeline run, with every figure checked against the filings.
        </p>
      )}
      <figcaption>
        {sentence
          ? `Written by an AI model from Tesla's ${sentence.form ?? "filing"} for ${sentence.quarterLabel}. `
          : null}
        {checked}
      </figcaption>
    </figure>
  );
}
