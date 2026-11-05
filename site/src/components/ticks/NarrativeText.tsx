import { Fragment, useId, type ReactNode } from "react";
import type { ClaimView } from "../../data/types";
import { TickNumber } from "./TickNumber";
import { formatClaimValue } from "./tickFormat";
import "./ticks.css";

export type NarrativeTextProps = {
  text: string;
  claims: ClaimView[];
  className?: string;
};

type Sentence = {
  /** 1-based, as sentence_ref counts them. */
  number: number;
  text: string;
  /** True when a blank line comes before this sentence. */
  startsParagraph: boolean;
};

type Wrap = {
  start: number;
  end: number;
  claim: ClaimView;
};

/** Splits on whitespace after . ? or !, keeping blank lines as paragraph breaks. */
export function splitSentences(text: string): Sentence[] {
  const trimmed = text.trim();
  if (!trimmed) return [];
  // With a capture group the separators come back at the odd indexes.
  const parts = trimmed.split(/(?<=[.?!])(\s+)/);
  const sentences: Sentence[] = [];
  let pendingBreak = false;
  parts.forEach((part, index) => {
    if (index % 2 === 1) {
      pendingBreak = /\n\s*\n/.test(part);
      return;
    }
    sentences.push({
      number: sentences.length + 1,
      text: part,
      startsParagraph: sentences.length === 0 || pendingBreak,
    });
    pendingBreak = false;
  });
  return sentences;
}

/**
 * Candidate spellings of a claim value as the prose might write it.
 * 28.05 gives "28.05"; -7.48 gives "7.48"; 486532 gives "486,532" and "486532".
 */
export function numberCandidates(value: number): string[] {
  const absolute = Math.abs(value);
  const plain = String(Number(absolute.toPrecision(12)));
  const [integer, fraction] = plain.split(".");
  const grouped = integer.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const withCommas = fraction === undefined ? grouped : `${grouped}.${fraction}`;
  return withCommas === plain ? [plain] : [withCommas, plain];
}

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Unit words and symbols that may follow a number, so that "$28.05B" or "21.1%" is one token. */
const TRAILING = /^(?:%|B(?![A-Za-z])|M(?![A-Za-z])|\s(?:percentage points|billion|million|thousand|percent|points|pts)\b)/;

/** Widens a number match to the whole token: a leading sign and $, and a trailing unit. */
function tokenSpan(sentence: string, start: number, end: number): { start: number; end: number } {
  let tokenStart = start;
  let tokenEnd = end;
  const trailing = TRAILING.exec(sentence.slice(tokenEnd));
  if (trailing) tokenEnd += trailing[0].length;
  if (sentence[tokenStart - 1] === "$") tokenStart -= 1;
  if (/[−+\-]/.test(sentence[tokenStart - 1] ?? "")) tokenStart -= 1;
  return { start: tokenStart, end: tokenEnd };
}

function overlaps(span: { start: number; end: number }, wraps: Wrap[]): boolean {
  return wraps.some((wrap) => span.start < wrap.end && span.end > wrap.start);
}

/**
 * Finds the token for one claim in one sentence: the earliest occurrence of any
 * spelling of its number that does not overlap a token already taken.
 */
function findToken(sentence: string, value: number, taken: Wrap[]): { start: number; end: number } | null {
  const found: { start: number; end: number }[] = [];
  for (const candidate of numberCandidates(value)) {
    const pattern = new RegExp(`(?<![\\d.,])${escapeRegExp(candidate)}(?!\\.?\\d)`, "g");
    for (const match of sentence.matchAll(pattern)) {
      const start = match.index ?? 0;
      found.push(tokenSpan(sentence, start, start + match[0].length));
    }
  }
  found.sort((a, b) => a.start - b.start);
  return found.find((span) => !overlaps(span, taken)) ?? null;
}

/** Assigns each claim to a token in its sentence. Returns the wraps per sentence and the claims that were not found. */
function placeClaims(sentences: Sentence[], claims: ClaimView[]) {
  const wrapsBySentence = new Map<number, Wrap[]>();
  const unmatched: ClaimView[] = [];
  for (const claim of claims) {
    const sentence = sentences.find((item) => String(item.number) === claim.sentence_ref);
    const taken = sentence ? (wrapsBySentence.get(sentence.number) ?? []) : [];
    const span = sentence ? findToken(sentence.text, claim.value, taken) : null;
    if (!sentence || !span) {
      unmatched.push(claim);
      continue;
    }
    const wraps = wrapsBySentence.get(sentence.number) ?? [];
    wraps.push({ ...span, claim });
    wrapsBySentence.set(sentence.number, wraps);
  }
  return { wrapsBySentence, unmatched };
}

function renderSentence(sentence: Sentence, wraps: Wrap[] | undefined, key: string) {
  const pieces: ReactNode[] = [];
  let cursor = 0;
  const ordered = [...(wraps ?? [])].sort((a, b) => a.start - b.start);
  ordered.forEach((wrap, index) => {
    pieces.push(sentence.text.slice(cursor, wrap.start));
    const token = sentence.text.slice(wrap.start, wrap.end);
    pieces.push(<TickNumber key={`${key}-${index}`} text={token} claim={wrap.claim} />);
    cursor = wrap.end;
  });
  pieces.push(sentence.text.slice(cursor));
  return pieces;
}

function UnmatchedClaims({ claims }: { claims: ClaimView[] }) {
  const titleId = useId();
  return (
    <section className="tick-unmatched" aria-labelledby={titleId}>
      <h3 id={titleId} className="tick-unmatched-title">
        Figures not found in the text
      </h3>
      <ul className="tick-unmatched-list">
        {claims.map((claim, index) => (
          <li key={`${claim.metric}-${claim.period}-${index}`}>
            <TickNumber text={formatClaimValue(claim.value, claim.unit)} claim={claim} />
          </li>
        ))}
      </ul>
    </section>
  );
}

/**
 * Memo or answer text with a tick on each figure its claims name. Sentences are
 * numbered from 1 across the whole text, as sentence_ref counts them. A claim
 * wraps at most one token, and a token is wrapped at most once. Claims the text
 * does not show are listed after it, still with their ticks.
 */
export function NarrativeText({ text, claims, className }: NarrativeTextProps) {
  const sentences = splitSentences(text);
  const { wrapsBySentence, unmatched } = placeClaims(sentences, claims);

  const paragraphs: Sentence[][] = [];
  sentences.forEach((sentence) => {
    if (sentence.startsParagraph || paragraphs.length === 0) {
      paragraphs.push([sentence]);
    } else {
      paragraphs[paragraphs.length - 1].push(sentence);
    }
  });

  return (
    <div className={className}>
      {paragraphs.map((group, index) => (
        <p key={group[0].number} className="narrative">
          {group.map((sentence, position) => (
            <Fragment key={sentence.number}>
              {position > 0 ? " " : null}
              {renderSentence(sentence, wrapsBySentence.get(sentence.number), `s${sentence.number}-p${index}`)}
            </Fragment>
          ))}
        </p>
      ))}
      {unmatched.length > 0 && <UnmatchedClaims claims={unmatched} />}
    </div>
  );
}
