"""Keyword guard for AI-written memo and Q&A text.

Code, not a model, rejects buy/sell language and price targets before anything is
published. Matching is case-insensitive and whole-word. The guard reports hits and
never rewrites text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Module constant: the phrases the guard flags. Each entry is a regex, matched
# case-insensitively. To extend the guard, add a regex here, keep it whole-word
# (wrap it in \b), and add a flagged example and a clean example to
# tests/test_keyword_guard.py. Variance language must keep passing.

# Words that turn a bare "buy" or "sell" into a recommendation about the stock.
_STOCK = r"stocks?|shares?|equity|TSLA|ratings?|positions?|recommendations?"
_VERB = r"buy|buys|buying|sell|sells|selling"
_WORD = r"[A-Za-z][A-Za-z'\-]*"
# "buy back" and "sell back" are buyback language, not recommendations.
_NOT_BACK = r"(?!\s+back\b)"
# A stock word may sit up to two words away from a verb, e.g. "buy the stock".
_FORWARD = rf"\b(?:{_VERB})\b{_NOT_BACK}(?:[ \t,]+{_WORD}){{0,2}}[ \t,:]+(?:{_STOCK})\b"
# The reverse order, e.g. "shares are a buy" or "rating: sell".
_REVERSE = rf"\b(?:{_STOCK})\b(?:[ \t,:]+{_WORD}){{0,2}}[ \t,:]+(?:{_VERB})\b{_NOT_BACK}"
# "upside of 25%" or "downside of $40" flag. A metric word right after the number
# (for example "downside of 8% to operating income") is scenario analysis and passes.
_UPSIDE = (
    r"\b(?:upside|downside)\s+(?:of|to)\s+(?:(?:about|roughly|around|nearly|approximately)\s+)?"
    r"(?:\$\s?\d[\d,.]*|\d[\d.,]*\s?%)"
    r"(?!\s+(?:\S+\s+){0,2}?(?:operating|gross|revenue|margin|earnings|income|cash|"
    r"deliveries|EPS|sales|expenses)\b)"
)

FLAGGED_PHRASES: tuple[str, ...] = (
    # Buy and sell recommendations.
    r"\bstrong\s+buy\b",
    r"\b(?:buy|sell)\s+now\b",
    _FORWARD,
    _REVERSE,
    r"\brated\s+(?:as\s+|at\s+)?(?:an?\s+)?(?:buy|sell)\b",
    r"\b(?:upgrade|downgrade)[sd]?\s+to\s+(?:an?\s+)?(?:buy|sell)\b",
    # Ratings. "outperformed" and "underperformed" are past tense and pass.
    r"\b(?:over|under)weight\b",
    r"\b(?:out|under)perform\b",
    # Recommendation language.
    r"\binvestors\s+should\b",
    r"\bwe\s+recommend\b",
    r"\baccumulate\b",
    r"\b(?:under|over)valued\b",
    # Price targets.
    r"\bprice\s+targets?\b",
    r"\btarget\s+prices?\b",
    r"\bfair\s+value\s+(?:estimate|model|target)\b",
    # "fair value" in accounting ("fair value of derivatives") passes. Only price forms flag.
    r"\bfair\s+value\s+(?:per\s+share\b|(?:is|at|near|around|about|to)\s+\$"
    r"|of\s+(?:the\s+)?(?:stock|shares?|equity|tsla|tesla)\b)",
    _UPSIDE,
    r"\b(?:TSLA|Tesla)\b[^.\n]{0,60}?\b(?:shares?|stock)\s+(?:are|is)\s+worth\b",
    r"\b(?:stock|share)\s+price\s+(?:targets?|should|to\s+(?:reach|hit)\b"
    r"|(?:of|at|near|around|to)\s+\$)",
)

# "$X per share" or "$X a share" is a price unless it reports EPS, a dividend or a
# buyback price. The reporting word must come earlier in the same sentence, with no
# target or valuation word between it and the amount, so "EPS was $0.52 per share
# and the target is $300 per share" still flags the $300.
_PER_SHARE = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?\s+(?:per|a)\s+share\b", re.IGNORECASE)
_REPORTED_PER_SHARE = re.compile(
    r"\b(?:EPS|earnings|income|diluted|basic|dividends?|repurchas\w*|buybacks?)\b",
    re.IGNORECASE,
)
_VALUATION_WORD = re.compile(r"\b(?:target\w*|worth|valu\w*|fair)\b", re.IGNORECASE)
_COMPILED = tuple(re.compile(pattern, re.IGNORECASE) for pattern in FLAGGED_PHRASES)


@dataclass(frozen=True)
class GuardHit:
    """One flagged phrase. ``start`` and ``end`` index into the checked text."""

    phrase: str
    start: int
    end: int
    text_kind: str


def _sentence_before(text: str, start: int) -> str:
    """Return the text between the last sentence break before ``start`` and ``start``."""
    before = text[:start]
    cut = max(
        before.rfind(". "),
        before.rfind("! "),
        before.rfind("? "),
        before.rfind("; "),
        before.rfind("\n"),
    )
    return before[cut + 1 :]


def check_text(text: str, text_kind: str) -> tuple[GuardHit, ...]:
    """Return every flagged phrase in ``text``, ordered by position."""
    hits: list[GuardHit] = []
    for pattern in _COMPILED:
        for match in pattern.finditer(text):
            hits.append(GuardHit(match.group(0), match.start(), match.end(), text_kind))
    for match in _PER_SHARE.finditer(text):
        before = _sentence_before(text, match.start())
        reported = list(_REPORTED_PER_SHARE.finditer(before))
        if reported and not _VALUATION_WORD.search(before[reported[-1].end() :]):
            continue
        hits.append(GuardHit(match.group(0), match.start(), match.end(), text_kind))
    return tuple(sorted(hits, key=lambda hit: (hit.start, hit.end)))


def check_narrative(memo_text: str, answers: dict[int, str]) -> tuple[GuardHit, ...]:
    """Check the memo first, then each Q&A answer in question-number order."""
    hits = list(check_text(memo_text, "memo"))
    for number in sorted(answers):
        hits.extend(check_text(answers[number], f"answer {number}"))
    return tuple(hits)
