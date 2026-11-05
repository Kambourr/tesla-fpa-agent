"""Narrate each published quarter: one memo per quarter, Q&A for the latest.

The model sees only the quarter's fact sheet (``agent.fact_sheet``). Questions
7 and 8 also get the backtest sheet, which covers all published quarters. The
model's claims are checked later by ``agent.verifier``. This module records
validation problems as ``issues`` and never raises for them. Re-asking is a
later task.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

import duckdb
from openai import OpenAI

from agent.fact_sheet import Fact, backtest_facts, quarter_facts
from agent.narrative import Answer, NarrativeDraft, PromptBundle, Question, load_prompts
from agent.settings import Settings

MEMO_WORDS = (150, 250)
ANSWER_WORDS = (60, 120)
ANSWER_NUMBERS = tuple(range(1, 11))
_SENTENCE_END = re.compile(r"(?<=[.?!])\s+")


class NarrationError(Exception):
    """Narration could not run, for example when no API key is set."""


@dataclass(frozen=True)
class DraftResult:
    draft: NarrativeDraft
    input_tokens: int
    output_tokens: int


class NarrationClient(Protocol):
    def draft(self, *, system: str, user: str, model: str, temperature: float) -> DraftResult: ...


class OpenAIClient:
    """The OpenAI Responses API with a structured NarrativeDraft output."""

    def __init__(self, settings: Settings | None = None) -> None:
        resolved = Settings() if settings is None else settings
        key = resolved.openai_api_key.get_secret_value()
        if not key:
            raise NarrationError("OPENAI_API_KEY is not set. Narration needs it to call the model.")
        self._client = OpenAI(api_key=key)

    def draft(self, *, system: str, user: str, model: str, temperature: float) -> DraftResult:
        response = self._client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            text_format=NarrativeDraft,
            temperature=temperature,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise NarrationError("the model returned no parsed narrative")
        usage = response.usage
        return DraftResult(
            draft=parsed,
            input_tokens=usage.input_tokens if usage is not None else 0,
            output_tokens=usage.output_tokens if usage is not None else 0,
        )


@dataclass(frozen=True)
class NarrationResult:
    quarter: str
    kind: str
    draft: NarrativeDraft
    input_hash: str
    input_tokens: int
    output_tokens: int
    issues: list[str]


def build_user_message(
    quarter: str,
    facts: Sequence[Fact],
    *,
    questions: Sequence[Question],
    backtest: Sequence[Fact],
) -> str:
    """The user message: the fact sheet as JSON, plus questions when asked.

    ``backtest_sheet`` appears only when questions are given, since only
    questions 7 and 8 need it.
    """
    payload: dict[str, Any] = {
        "quarter": quarter,
        "fact_sheet": [fact.as_json() for fact in facts],
        "questions": [{"number": q.number, "text": q.text} for q in questions],
    }
    if questions:
        payload["backtest_sheet"] = [fact.as_json() for fact in backtest]
    return json.dumps(payload, indent=1)


def input_hash(user: str, prompts: PromptBundle, model: str) -> str:
    """Cache key: the user message, the prompt version and content, and the model."""
    material = json.dumps([user, prompts.cache_material, model])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def validate_draft(draft: NarrativeDraft, *, with_questions: bool) -> list[str]:
    """Return the problems found in one draft. An empty list means none."""
    issues: list[str] = []
    memo_words = _word_count(draft.memo.text)
    low, high = MEMO_WORDS
    if not low <= memo_words <= high:
        issues.append(f"memo has {memo_words} words, outside {low} to {high}")
    issues.extend(_claim_issues("memo", draft.memo.text, draft.memo.claims))

    numbers = sorted(answer.question_number for answer in draft.answers)
    if with_questions:
        if numbers != list(ANSWER_NUMBERS):
            issues.append(f"answers are for questions {numbers}, expected 1 through 10 once each")
    elif draft.answers:
        issues.append(f"answers were returned without questions: {numbers}")

    for answer in draft.answers:
        issues.extend(_answer_issues(answer))
    return issues


def narrate_quarter(
    connection: duckdb.DuckDBPyConnection,
    quarter: str,
    client: NarrationClient,
    *,
    prompts: PromptBundle,
    model: str,
    with_questions: bool,
) -> NarrationResult:
    facts = quarter_facts(connection, quarter)
    questions = list(prompts.questions) if with_questions else []
    backtest = backtest_facts(connection) if with_questions else ()
    user = build_user_message(quarter, facts, questions=questions, backtest=backtest)
    result = client.draft(
        system=prompts.memo_instructions,
        user=user,
        model=model,
        temperature=prompts.temperature,
    )
    return NarrationResult(
        quarter=quarter,
        kind="memo+qa" if with_questions else "memo",
        draft=result.draft,
        input_hash=input_hash(user, prompts, model),
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        issues=validate_draft(result.draft, with_questions=with_questions),
    )


def narrate_all(
    connection: duckdb.DuckDBPyConnection,
    client: NarrationClient,
    *,
    prompts: PromptBundle | None = None,
    model: str | None = None,
) -> list[NarrationResult]:
    """One memo per published quarter with a forecast, oldest first.

    The latest such quarter also gets the ten questions. Nothing is written to
    the database; call ``store_narration`` to keep a result.
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
        narrate_quarter(
            connection,
            quarter,
            client,
            prompts=bundle,
            model=chosen_model,
            with_questions=quarter == latest,
        )
        for quarter in quarters
    ]


def store_narration(
    connection: duckdb.DuckDBPyConnection,
    result: NarrationResult,
    prompts: PromptBundle,
    model: str,
) -> None:
    """Write the result to ``narrative``, replacing the quarter's row."""
    connection.execute(
        """
        INSERT OR REPLACE INTO narrative VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            result.quarter,
            result.kind,
            result.input_hash,
            prompts.version,
            model,
            result.draft.model_dump_json(),
            result.input_tokens,
            result.output_tokens,
            json.dumps(result.issues),
            datetime.now(UTC).replace(tzinfo=None),
        ],
    )


def _answer_issues(answer: Answer) -> list[str]:
    label = f"answer {answer.question_number}"
    issues: list[str] = []
    low, high = ANSWER_WORDS
    words = _word_count(answer.text)
    if not low <= words <= high:
        issues.append(f"{label} has {words} words, outside {low} to {high}")
    issues.extend(_claim_issues(label, answer.text, answer.claims))
    return issues


def _claim_issues(label: str, text: str, claims: Sequence[Any]) -> list[str]:
    sentences = _sentence_count(text)
    issues: list[str] = []
    for claim in claims:
        try:
            ref = int(claim.sentence_ref)
        except ValueError:
            issues.append(f"{label}: sentence_ref '{claim.sentence_ref}' is not a number")
            continue
        if ref < 1:
            issues.append(f"{label}: sentence_ref {ref} is below 1")
        elif ref > sentences:
            issues.append(f"{label}: sentence_ref {ref} is past the {sentences} sentences")
    return issues


def _sentence_count(text: str) -> int:
    return len([part for part in _SENTENCE_END.split(text.strip()) if part])


def _word_count(text: str) -> int:
    return len(text.split())
