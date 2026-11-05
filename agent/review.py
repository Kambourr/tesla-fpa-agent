"""Verify each narration draft, re-ask the model once with the errors, keep what remains.

Nothing in this module edits a draft. A claim's value, unit, metric and text are
the model's own words. When the second draft still has problems it is stored
with its flags, and the verifier's expected values are shown beside it. Only a
draft with no flags, no unsupported claims, no guard hits and no validation
issues is marked verified.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import duckdb

from agent.fact_sheet import Fact, backtest_facts, quarter_facts
from agent.keyword_guard import GuardHit, check_narrative
from agent.narrate import (
    NarrationClient,
    NarrationResult,
    build_user_message,
    mark_verified,
    narrate_quarter,
    store_narration,
    validate_draft,
)
from agent.narrative import NarrativeDraft, PromptBundle, load_prompts
from agent.settings import Settings
from agent.verifier import ClaimResult, Status, summarize, verify_claims

CORRECTIONS_HEADER = "\n\nCorrections needed:\n"
CORRECTIONS_FOOTER = "Return the full corrected JSON. Keep every other sentence unchanged."


@dataclass(frozen=True)
class LocatedResult:
    """One claim's verifier result, with where it came from: "memo" or "answer N"."""

    location: str
    result: ClaimResult


@dataclass(frozen=True)
class Review:
    results: tuple[LocatedResult, ...]
    guard_hits: tuple[GuardHit, ...]
    issues: tuple[str, ...]
    counts: dict[str, int]

    @property
    def clean(self) -> bool:
        return (
            self.counts["flagged"] == 0
            and self.counts["unsupported"] == 0
            and not self.guard_hits
            and not self.issues
        )


@dataclass(frozen=True)
class ReviewedNarration:
    """The final narration and its review.

    ``input_tokens`` and ``output_tokens`` sum every model call made for this
    quarter. ``narration`` carries the same totals, so the stored row records
    the full spend. A cached result made no calls, so both are zero.
    """

    narration: NarrationResult
    review: Review
    reasked: bool
    first_review: Review | None
    input_tokens: int
    output_tokens: int


def review_draft(
    draft: NarrativeDraft,
    facts: Sequence[Fact],
    *,
    quarter: str,
    latest: bool,
) -> Review:
    """Check one draft against its fact sheet, the keyword guard and validation.

    ``facts`` is the quarter's fact sheet, plus the backtest sheet for the
    latest quarter. ``latest`` is True when the draft carries the ten answers.
    """
    if not facts:
        raise ValueError(f"no fact sheet for {quarter}")
    fact_tuple = tuple(facts)
    located = [LocatedResult("memo", r) for r in verify_claims(draft.memo.claims, fact_tuple)]
    for answer in draft.answers:
        label = f"answer {answer.question_number}"
        located.extend(LocatedResult(label, r) for r in verify_claims(answer.claims, fact_tuple))
    answers = {answer.question_number: answer.text for answer in draft.answers}
    results = tuple(located)
    return Review(
        results=results,
        guard_hits=check_narrative(draft.memo.text, answers),
        issues=tuple(validate_draft(draft, with_questions=latest)),
        counts=summarize(item.result for item in results),
    )


def first_review_record(review: Review) -> dict[str, Any]:
    """What the verifier found in a first draft, as JSON-ready data.

    ``catches`` lists each flagged or unsupported claim with what the model wrote
    and what the fact sheet holds. Numbers are kept as strings so the record is
    exact; the publish step turns them into floats.
    """
    catches = [
        {
            "location": item.location,
            "metric": item.result.claim.metric,
            "period": item.result.claim.period,
            "sentence_ref": item.result.claim.sentence_ref,
            "written": str(item.result.claim.value),
            "unit": item.result.claim.unit,
            "expected": None if item.result.expected is None else str(item.result.expected),
            "expected_unit": item.result.expected_unit,
            "status": item.result.status.value,
            "source": item.result.source,
        }
        for item in review.results
        if item.result.status is not Status.VERIFIED
    ]
    return {
        "checked": review.counts["total"],
        "verified": review.counts["verified"],
        "flagged": review.counts["flagged"],
        "unsupported": review.counts["unsupported"],
        "guard_hits": [f"{hit.text_kind}: {hit.phrase}" for hit in review.guard_hits],
        "issues": list(review.issues),
        "catches": catches,
    }


def _store_first_review(
    connection: duckdb.DuckDBPyConnection, quarter: str, record: dict[str, Any]
) -> None:
    connection.execute(
        "UPDATE narrative SET first_review = ? WHERE quarter = ?",
        [json.dumps(record, sort_keys=True), quarter],
    )


def correction_message(review: Review) -> str:
    """Plain text listing each problem, for the model's second call."""
    lines: list[str] = []
    for item in review.results:
        result = item.result
        claim = result.claim
        if result.status is Status.FLAGGED:
            lines.append(
                f"In {item.location}, sentence {claim.sentence_ref}: you wrote "
                f"{_plain(claim.value)} {claim.unit} for {claim.metric} ({claim.period}); "
                f"the fact sheet value is {_plain(result.expected)} {result.expected_unit}."
            )
        elif result.status is Status.UNSUPPORTED:
            lines.append(
                f"In {item.location}, sentence {claim.sentence_ref}: {claim.metric} for "
                f"{claim.period} is not on the fact sheet; use only listed keys and periods."
            )
    for hit in review.guard_hits:
        lines.append(f"In {hit.text_kind}, remove the phrase '{hit.phrase}'.")
    lines.extend(review.issues)
    lines.append(CORRECTIONS_FOOTER)
    return "\n".join(lines)


def narrate_and_review(
    connection: duckdb.DuckDBPyConnection,
    quarter: str,
    client: NarrationClient,
    *,
    prompts: PromptBundle,
    model: str,
    with_questions: bool,
    force: bool = False,
) -> ReviewedNarration:
    """Narrate one quarter, review it, and re-ask the model at most once.

    A cached result is returned as it is, with no re-ask. Otherwise a draft with
    problems is sent back once with the corrections. The final draft is stored,
    and marked verified only when its review is clean.
    """
    result = narrate_quarter(
        connection,
        quarter,
        client,
        prompts=prompts,
        model=model,
        with_questions=with_questions,
        force=force,
    )
    user, verification_facts = _sheets(connection, quarter, prompts, with_questions)
    review = review_draft(result.draft, verification_facts, quarter=quarter, latest=with_questions)
    if result.cached:
        return ReviewedNarration(
            narration=result,
            review=review,
            reasked=False,
            first_review=None,
            input_tokens=0,
            output_tokens=0,
        )

    if review.clean:
        store_narration(connection, result, prompts, model)
        _store_first_review(connection, quarter, first_review_record(review))
        mark_verified(connection, quarter, result.input_hash)
        return ReviewedNarration(
            narration=result,
            review=review,
            reasked=False,
            first_review=None,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )

    second = client.draft(
        system=prompts.memo_instructions,
        user=user + CORRECTIONS_HEADER + correction_message(review),
        model=model,
        temperature=prompts.temperature,
    )
    input_total = result.input_tokens + second.input_tokens
    output_total = result.output_tokens + second.output_tokens
    final = NarrationResult(
        quarter=quarter,
        kind=result.kind,
        draft=second.draft,
        input_hash=result.input_hash,
        input_tokens=input_total,
        output_tokens=output_total,
        issues=validate_draft(second.draft, with_questions=with_questions),
    )
    final_review = review_draft(
        final.draft, verification_facts, quarter=quarter, latest=with_questions
    )
    store_narration(connection, final, prompts, model)
    _store_first_review(connection, quarter, first_review_record(review))
    if final_review.clean:
        mark_verified(connection, quarter, final.input_hash)
    return ReviewedNarration(
        narration=final,
        review=final_review,
        reasked=True,
        first_review=review,
        input_tokens=input_total,
        output_tokens=output_total,
    )


def review_all(
    connection: duckdb.DuckDBPyConnection,
    client: NarrationClient,
    *,
    prompts: PromptBundle | None = None,
    model: str | None = None,
    force: bool = False,
) -> list[ReviewedNarration]:
    """Narrate and review each published quarter with a forecast, oldest first.

    The quarter selection matches ``agent.narrate.narrate_all``; the latest
    quarter also gets the ten questions. Nothing is written except through
    ``narrate_and_review``.
    """
    bundle = load_prompts() if prompts is None else prompts
    chosen_model = Settings().openai_model if model is None else model
    rows = connection.execute(
        """
        SELECT quarter FROM published_quarter
        WHERE kind = 'backtest' AND has_forecast
        ORDER BY quarter
        """
    ).fetchall()
    quarters = [row[0] for row in rows]
    latest = quarters[-1] if quarters else None
    return [
        narrate_and_review(
            connection,
            quarter,
            client,
            prompts=bundle,
            model=chosen_model,
            with_questions=quarter == latest,
            force=force,
        )
        for quarter in quarters
    ]


def _sheets(
    connection: duckdb.DuckDBPyConnection,
    quarter: str,
    prompts: PromptBundle,
    with_questions: bool,
) -> tuple[str, tuple[Fact, ...]]:
    """The user message and the verification facts, built as narrate_quarter builds them.

    The verification facts are the quarter's sheet, plus the backtest sheet when
    the draft carries questions 7 and 8.
    """
    facts = quarter_facts(connection, quarter)
    questions = list(prompts.questions) if with_questions else []
    backtest = backtest_facts(connection) if with_questions else ()
    user = build_user_message(quarter, facts, questions=questions, backtest=backtest)
    return user, tuple(facts) + tuple(backtest)


def _plain(value: float | Decimal | None) -> str:
    """A number without exponent notation, for the correction text."""
    if value is None:
        return "(none)"
    return format(Decimal(str(value)).normalize(), "f")
