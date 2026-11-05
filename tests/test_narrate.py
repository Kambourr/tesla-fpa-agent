"""Narration on a fixture database, with a fake client. No network calls."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import duckdb
import pytest
from pydantic import SecretStr

from agent.fact_sheet import backtest_facts, quarter_facts
from agent.model_stage import run_model, run_variance
from agent.narrate import (
    DraftResult,
    NarrationError,
    OpenAIClient,
    build_user_message,
    input_hash,
    narrate_all,
    narrate_quarter,
    store_narration,
    validate_draft,
)
from agent.narrative import Answer, Claim, Memo, NarrativeDraft, PromptBundle, load_prompts
from agent.settings import Settings
from pipeline_fixture import build_database

PUBLISHED = (
    "2023-Q4",
    "2024-Q1",
    "2024-Q2",
    "2024-Q3",
    "2024-Q4",
    "2025-Q1",
    "2025-Q2",
    "2025-Q3",
    "2025-Q4",
    "2026-Q1",
    "2026-Q2",
    "2026-Q3",
)
LATEST = PUBLISHED[-1]
FACT_FIELDS = {"key", "period", "value", "unit", "source", "source_url"}


@dataclass(frozen=True)
class Call:
    system: str
    user: str
    model: str
    temperature: float


@dataclass
class FakeClient:
    """Records each call and answers with a draft built from the sheet it was sent."""

    calls: list[Call] = field(default_factory=list)

    def draft(self, *, system: str, user: str, model: str, temperature: float) -> DraftResult:
        self.calls.append(Call(system, user, model, temperature))
        return DraftResult(draft=_canned(user), input_tokens=1200, output_tokens=640)


@pytest.fixture
def connection() -> duckdb.DuckDBPyConnection:
    database = build_database()
    run_model(database, publish_forward=False)
    run_variance(database)
    return database


@pytest.fixture
def prompts() -> PromptBundle:
    return load_prompts()


def _canned(user: str) -> NarrativeDraft:
    """A draft whose numbers are read from the fact sheet in the message."""
    payload = json.loads(user)
    quarter = payload["quarter"]
    facts = {fact["key"]: fact for fact in payload["fact_sheet"]}
    deliveries = float(facts["actual.deliveries"]["value"])
    revenue_million = round(float(facts["actual.total_revenue"]["value"]) / 1_000_000, 1)
    margin = round(float(facts["actual.gross_margin"]["value"]), 1)
    sentences = [
        f"Deliveries were {int(deliveries):,} vehicles in {quarter}.",
        f"Total revenue was {revenue_million:,.1f} million dollars.",
        f"Gross margin was {margin:.1f} percent.",
    ]
    claims = [
        Claim(
            metric="actual.deliveries",
            period=quarter,
            value=deliveries,
            unit="units",
            sentence_ref="1",
        ),
        Claim(
            metric="actual.total_revenue",
            period=quarter,
            value=revenue_million,
            unit="USD million",
            sentence_ref="2",
        ),
        Claim(
            metric="actual.gross_margin",
            period=quarter,
            value=margin,
            unit="percent",
            sentence_ref="3",
        ),
    ]
    memo = Memo(text=_text(sentences, 200), claims=claims)
    answers: list[Answer] = []
    if payload["questions"]:
        answers = [
            Answer(
                question_number=number,
                text=_text([f"Answer {number} draws on the sheet."], 80),
                claims=[],
            )
            for number in range(1, 11)
        ]
    return NarrativeDraft(memo=memo, answers=answers)


def _text(sentences: list[str], total_words: int) -> str:
    """Join the sentences, then add one filler sentence so the text has total_words words."""
    parts = list(sentences)
    lead = sum(len(sentence.split()) for sentence in sentences)
    if total_words > lead:
        filler = total_words - lead
        parts.append(" ".join(["plain"] * (filler - 1) + ["close."]))
    return " ".join(parts)


def _draft(text: str, claims: list[Claim], answers: list[Answer] | None = None) -> NarrativeDraft:
    return NarrativeDraft(memo=Memo(text=text, claims=claims), answers=answers or [])


def _claim(ref: str) -> Claim:
    return Claim(metric="actual.deliveries", period=LATEST, value=1, unit="units", sentence_ref=ref)


def test_twelve_memos_and_only_the_latest_gets_answers(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    client = FakeClient()
    results = narrate_all(connection, client, prompts=prompts, model="test-model")

    assert [result.quarter for result in results] == list(PUBLISHED)
    assert [result.kind for result in results] == ["memo"] * 11 + ["memo+qa"]
    assert [len(result.draft.answers) for result in results] == [0] * 11 + [10]
    latest_numbers = sorted(answer.question_number for answer in results[-1].draft.answers)
    assert latest_numbers == list(range(1, 11))
    assert [json.loads(call.user)["quarter"] for call in client.calls] == list(PUBLISHED)
    assert all(result.issues == [] for result in results)
    assert all(result.input_tokens == 1200 for result in results)


def test_default_model_comes_from_settings(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    client = FakeClient()
    narrate_all(connection, client, prompts=prompts)
    assert {call.model for call in client.calls} == {Settings().openai_model}


def test_non_latest_message_holds_only_the_fact_sheet(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    client = FakeClient()
    narrate_quarter(connection, "2024-Q1", client, prompts=prompts, model="m", with_questions=False)
    payload = json.loads(client.calls[0].user)

    assert set(payload) == {"quarter", "fact_sheet", "questions"}
    assert payload["quarter"] == "2024-Q1"
    assert payload["questions"] == []
    sheet = [fact.as_json() for fact in quarter_facts(connection, "2024-Q1")]
    assert payload["fact_sheet"] == sheet
    assert all(set(entry) == FACT_FIELDS for entry in payload["fact_sheet"])
    assert all(isinstance(entry["value"], str) for entry in payload["fact_sheet"])


def test_latest_message_adds_backtest_sheet_and_questions_seven_and_eight(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    client = FakeClient()
    narrate_quarter(connection, LATEST, client, prompts=prompts, model="m", with_questions=True)
    payload = json.loads(client.calls[0].user)

    assert set(payload) == {"quarter", "fact_sheet", "questions", "backtest_sheet"}
    numbers = [question["number"] for question in payload["questions"]]
    assert numbers == list(range(1, 11))
    texts = {question["number"]: question["text"] for question in payload["questions"]}
    assert "12 published quarters" in texts[7]
    assert "12 published quarters" in texts[8]
    assert payload["backtest_sheet"] == [fact.as_json() for fact in backtest_facts(connection)]
    assert {fact["period"] for fact in payload["backtest_sheet"]} >= {LATEST, "12Q"}


def test_build_user_message_omits_backtest_when_no_questions(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    facts = quarter_facts(connection, LATEST)
    text = build_user_message(LATEST, facts, questions=[], backtest=())
    assert "backtest_sheet" not in json.loads(text)


def test_validation_passes_a_200_word_memo_with_valid_claims() -> None:
    text = _text(["One fact is here.", "Another fact is here."], 200)
    assert len(text.split()) == 200
    draft = _draft(text, [_claim("1"), _claim("2")])
    assert validate_draft(draft, with_questions=False) == []


def test_validation_flags_a_100_word_memo() -> None:
    text = _text(["One fact is here.", "Another fact is here."], 100)
    issues = validate_draft(_draft(text, [_claim("1")]), with_questions=False)
    assert any("words" in issue and "150" in issue for issue in issues)


def test_validation_flags_answers_on_a_non_latest_draft() -> None:
    text = _text(["One fact is here."], 200)
    answer = Answer(question_number=1, text=_text(["An answer."], 80), claims=[])
    issues = validate_draft(_draft(text, [], [answer]), with_questions=False)
    assert any("without questions" in issue for issue in issues)


def test_validation_flags_a_sentence_ref_past_the_last_sentence() -> None:
    text = _text(["First fact.", "Second fact."], 200)
    issues = validate_draft(_draft(text, [_claim("9")]), with_questions=False)
    assert any("sentence_ref 9" in issue for issue in issues)


def test_validation_flags_a_bad_sentence_ref_and_a_wrong_answer_set() -> None:
    text = _text(["First fact."], 200)
    issues = validate_draft(_draft(text, [_claim("two")]), with_questions=False)
    assert any("not a number" in issue for issue in issues)

    answers = [
        Answer(question_number=number, text=_text(["An answer."], 80), claims=[])
        for number in range(1, 10)
    ]
    issues = validate_draft(_draft(text, [], answers), with_questions=True)
    assert any("expected 1 through 10" in issue for issue in issues)


def test_input_hash_changes_with_model_or_prompt_version_and_is_otherwise_stable(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    def run(model: str, bundle: PromptBundle) -> str:
        return narrate_quarter(
            connection,
            LATEST,
            FakeClient(),
            prompts=bundle,
            model=model,
            with_questions=True,
        ).input_hash

    base = run("model-a", prompts)
    assert run("model-a", prompts) == base
    assert run("model-b", prompts) != base
    newer = prompts.model_copy(update={"version": "2099-01-01.1"})
    assert run("model-a", newer) != base
    assert input_hash("x", prompts, "m") == input_hash("x", prompts, "m")
    assert input_hash("x", prompts, "m") != input_hash("y", prompts, "m")


def test_store_narration_writes_and_replaces_the_row(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    first = narrate_quarter(
        connection, LATEST, FakeClient(), prompts=prompts, model="model-a", with_questions=True
    )
    store_narration(connection, first, prompts, "model-a")

    second = narrate_quarter(
        connection, LATEST, FakeClient(), prompts=prompts, model="model-b", with_questions=True
    )
    store_narration(connection, second, prompts, "model-b")

    rows = connection.execute(
        """
        SELECT kind, input_hash, prompt_version, model, payload, input_tokens,
               output_tokens, issues
        FROM narrative WHERE quarter = ?
        """,
        [LATEST],
    ).fetchall()
    assert len(rows) == 1
    kind, digest, version, model, payload, tokens_in, tokens_out, issues = rows[0]
    assert kind == "memo+qa"
    assert digest == second.input_hash
    assert version == prompts.version
    assert model == "model-b"
    assert json.loads(payload) == json.loads(second.draft.model_dump_json())
    assert (tokens_in, tokens_out) == (1200, 640)
    assert json.loads(issues) == []
    count = connection.execute("SELECT count(*) FROM narrative").fetchone()
    assert count == (1,)


def test_openai_client_refuses_an_empty_key() -> None:
    with pytest.raises(NarrationError, match="OPENAI_API_KEY"):
        OpenAIClient(Settings(openai_api_key=SecretStr("")))


def test_temperature_passed_to_the_client_is_the_prompt_temperature(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    client = FakeClient()
    narrate_all(connection, client, prompts=prompts, model="m")
    temperatures = {call.temperature for call in client.calls}
    assert temperatures == {prompts.temperature}
    assert prompts.temperature <= 0.3
    assert all(call.system == prompts.memo_instructions for call in client.calls)


def test_openai_client_retries_without_temperature_when_the_model_rejects_it() -> None:
    from openai import BadRequestError

    from agent.narrate import OpenAIClient
    from agent.narrative import Memo, NarrativeDraft
    from agent.settings import Settings

    calls: list[dict] = []
    draft = NarrativeDraft(memo=Memo(text="x", claims=[]), answers=[])

    class FakeResponses:
        def parse(self, **kwargs):
            calls.append(kwargs)
            if "temperature" in kwargs:
                # Built without the SDK's transport types; only the class and message matter.
                error = BadRequestError.__new__(BadRequestError)
                Exception.__init__(
                    error, "Unsupported parameter: 'temperature' is not supported with this model."
                )
                raise error
            usage = type("Usage", (), {"input_tokens": 3, "output_tokens": 2})()
            return type("Resp", (), {"output_parsed": draft, "usage": usage})()

    client = OpenAIClient(Settings(openai_api_key="test-key-placeholder", _env_file=None))
    client._client = type("Fake", (), {"responses": FakeResponses()})()
    result = client.draft(system="s", user="u", model="m", temperature=0.2)
    assert result.draft == draft
    assert [("temperature" in call) for call in calls] == [True, False]
