import { placeClaims, splitSentences, type Wrap } from "../components/ticks/NarrativeText";
import type { ClaimView, QuarterView } from "../data/types";
import { checkFigure, type CheckResult } from "../verify/verifier";

/** One editable figure: where it sits in the excerpt and what the model claimed. */
export interface Figure {
  id: string;
  claim: ClaimView;
  /** Text before the number inside the token, e.g. "$". */
  prefix: string;
  /** The number as written, e.g. "28.05". */
  number: string;
  /** Text after the number inside the token, e.g. " billion". */
  suffix: string;
}

export type Piece = { kind: "text"; text: string } | { kind: "figure"; figure: Figure };

export interface Excerpt {
  pieces: Piece[];
  figures: Figure[];
}

const NUMBER = /\d[\d,]*(?:\.\d+)?|\.\d+/;

/**
 * The first sentences of a memo, cut into text and figures. Only figures with
 * a published expected value are editable (an unsupported claim has nothing to
 * check against). Takes sentences until `maxFigures` figures are covered.
 */
export function buildExcerpt(quarter: QuarterView, maxSentences = 2): Excerpt | null {
  const memo = quarter.memo;
  if (!memo) return null;
  const sentences = splitSentences(memo.text);
  const { wrapsBySentence } = placeClaims(sentences, memo.claims);
  const pieces: Piece[] = [];
  const figures: Figure[] = [];
  sentences.slice(0, maxSentences).forEach((sentence, sentenceIndex) => {
    if (sentenceIndex > 0) pieces.push({ kind: "text", text: " " });
    const wraps: Wrap[] = [...(wrapsBySentence.get(sentence.number) ?? [])].sort(
      (a, b) => a.start - b.start,
    );
    let cursor = 0;
    for (const wrap of wraps) {
      const token = sentence.text.slice(wrap.start, wrap.end);
      const match = NUMBER.exec(token);
      if (!match || wrap.claim.expected === null || wrap.claim.expected_unit === null) {
        continue;
      }
      pieces.push({ kind: "text", text: sentence.text.slice(cursor, wrap.start) });
      const figure: Figure = {
        id: `f${figures.length}`,
        claim: wrap.claim,
        prefix: token.slice(0, match.index),
        number: match[0],
        suffix: token.slice(match.index + match[0].length),
      };
      figures.push(figure);
      pieces.push({ kind: "figure", figure });
      cursor = wrap.end;
    }
    pieces.push({ kind: "text", text: sentence.text.slice(cursor) });
  });
  return figures.length > 0 ? { pieces, figures } : null;
}

/**
 * The value the code checks for an edit. Prose writes magnitudes ("$7.48
 * billion below forecast") while the model's structured claim carries the sign,
 * so an edit keeps the claim's sign; a leading minus flips it.
 */
export function editedValueText(figure: Figure, typed: string): string {
  const cleaned = typed.replace(/[,\s]/g, "").replace(/^[−–]/, "-");
  const flip = cleaned.startsWith("-");
  const magnitude = cleaned.replace(/^[-+]/, "");
  const negative = figure.claim.value < 0 !== flip;
  return `${negative ? "-" : ""}${magnitude}`;
}

export function checkEdit(figure: Figure, typed: string, unit: string): CheckResult {
  return checkFigure(
    editedValueText(figure, typed),
    unit,
    figure.claim.expected as number,
    figure.claim.expected_unit as string,
  );
}

/** Units a visitor can switch a figure to, in the same family as the claim's. */
export function unitChoices(claim: ClaimView): string[] {
  switch (claim.expected_unit) {
    case "USD":
      return ["USD billion", "USD million", "USD thousand", "USD"];
    case "percent":
      return [claim.unit, claim.unit === "percent" ? "percentage points" : "percent"];
    case "units":
      return claim.unit.includes("thousand")
        ? [claim.unit, "units"]
        : [claim.unit, "thousand units"];
    default:
      return [claim.unit];
  }
}

/** The rule in words, for the inspector. */
export function ruleText(expectedUnit: string | null): string {
  switch (expectedUnit) {
    case "USD":
    case "USD_per_unit":
      return "Dollar figures must be within 0.5% of the source, with the right sign.";
    case "percent":
      return "Percentages must be within 0.1 percentage points.";
    default:
      return "Vehicle counts must match exactly, at the precision written.";
  }
}
