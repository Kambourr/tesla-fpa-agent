"""Narrate each published quarter: one memo per quarter, Q&A for the latest.

The model sees only the quarter's fact sheet (``agent.fact_sheet``). Questions
7 and 8 also get the backtest sheet, which covers all published quarters. The
model's claims are checked later by ``agent.verifier``. This module records
validation problems as ``issues`` and never raises for them. Re-asking is a
later task.

Cache: a stored narration is reused when its input hash, kind, and quarter
match and its ``verified`` flag is set (see ``mark_verified``). Only verified
text is reused. ``force`` skips the cache.
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
from openai import BadRequestError, OpenAI

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
        # Trim whitespace a pasted secret can carry; a key never contains spaces.
        key = resolved.openai_api_key.get_secret_value().strip()
        if not key:
            raise NarrationError("OPENAI_API_KEY is not set. Narration needs it to call the model.")
        self._client = OpenAI(api_key=key)

    def draft(self, *, system: str, user: str, model: str, temperature: float) -> DraftResult:
        request = {
            "model": model,
            "input": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "text_format": NarrativeDraft,
        }
        try:
            response = self._client.responses.parse(**request, temperature=temperature)
        except BadRequestError as error:
            # Some models fix their sampling and reject a temperature parameter.
            # Retry once without it rather than fail the run; anything else re-raises.
            if "temperature" not in str(error).lower():
                raise
            response = self._client.responses.parse(**request)
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
    cached: bool = False


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
    force: bool = False,
) -> NarrationResult:
    """Return the verified stored narration when it matches, else call the model.

    The user message and input hash are built first. A hit needs a stored row
    for this quarter and kind with the same hash and ``verified`` set. Then the
    client is not called. ``force=True`` calls the client even on a hit.
    """
    facts = quarter_facts(connection, quarter)
    questions = list(prompts.questions) if with_questions else []
    backtest = backtest_facts(connection) if with_questions else ()
    user = build_user_message(quarter, facts, questions=questions, backtest=backtest)
    kind = "memo+qa" if with_questions else "memo"
    digest = input_hash(user, prompts, model)
    if not force:
        hit = _verified_result(connection, quarter, kind, digest)
        if hit is not None:
            return hit
    result = client.draft(
        system=prompts.memo_instructions,
        user=user,
        model=model,
        temperature=prompts.temperature,
    )
    return NarrationResult(
        quarter=quarter,
        kind=kind,
        draft=result.draft,
        input_hash=digest,
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
    force: bool = False,
) -> list[NarrationResult]:
    """One memo per published quarter with a forecast, oldest first.

    The latest such quarter also gets the ten questions. A verified stored
    narration is reused unless ``force`` is set. Nothing is written to the
    database; call ``store_narration`` to keep a result.
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
            force=force,
        )
        for quarter in quarters
    ]


def store_narration(
    connection: duckdb.DuckDBPyConnection,
    result: NarrationResult,
    prompts: PromptBundle,
    model: str,
) -> None:
    """Write the result to ``narrative``, replacing the quarter's row.

    A freshly drafted result is stored unverified until ``mark_verified`` is
    called for its hash. A cached result came from a verified row, so it stays
    verified.
    """
    connection.execute(
        """
        INSERT OR REPLACE INTO narrative (
            quarter, kind, input_hash, prompt_version, model, payload,
            input_tokens, output_tokens, issues, created_at, verified
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            result.cached,
        ],
    )


def mark_verified(connection: duckdb.DuckDBPyConnection, quarter: str, input_hash: str) -> None:
    """Set ``verified`` on the quarter's stored row, only if its hash matches.

    Call this after the verifier has passed the stored draft's claims. A row
    stored under a different hash is left unchanged.
    """
    connection.execute(
        "UPDATE narrative SET verified = TRUE WHERE quarter = ? AND input_hash = ?",
        [quarter, input_hash],
    )


def _verified_result(
    connection: duckdb.DuckDBPyConnection,
    quarter: str,
    kind: str,
    digest: str,
) -> NarrationResult | None:
    """The stored verified narration for this input, or None when there is none."""
    row = connection.execute(
        """
        SELECT payload, issues FROM narrative
        WHERE quarter = ? AND kind = ? AND input_hash = ? AND verified = TRUE
        """,
        [quarter, kind, digest],
    ).fetchone()
    if row is None:
        return None
    payload, issues = row
    return NarrationResult(
        quarter=quarter,
        kind=kind,
        draft=NarrativeDraft.model_validate_json(payload),
        input_hash=digest,
        input_tokens=0,
        output_tokens=0,
        issues=list(json.loads(issues)),
        cached=True,
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
