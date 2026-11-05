"""Verify, re-ask once, and keep the flags that remain. Fixture database, no network.

Every client here is either the scripted client below (it fails on any call it
was not given a draft for) or ``FakeClient`` from test_narrate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

import duckdb
import pytest

from agent.fact_sheet import Fact, backtest_facts, quarter_facts
from agent.model_stage import run_model, run_variance
from agent.narrate import DraftResult, input_hash, narrate_quarter
from agent.narrative import Answer, Claim, Memo, NarrativeDraft, PromptBundle, load_prompts
from agent.review import (
    correction_message,
    narrate_and_review,
    review_all,
    review_draft,
)
from agent.verifier import Status
from pipeline_fixture import build_database
from test_narrate import LATEST, PUBLISHED, Call, FakeClient, _text

QUARTER = "2024-Q1"
MODEL = "test-model"
CORRECTIONS = "\n\nCorrections needed:\n"


@dataclass
class ScriptedClient:
    """Returns the scripted drafts in order. An unscripted call is a test failure."""

    drafts: list[NarrativeDraft]
    calls: list[Call] = field(default_factory=list)

    def draft(self, *, system: str, user: str, model: str, temperature: float) -> DraftResult:
        self.calls.append(Call(system, user, model, temperature))
        if len(self.calls) > len(self.drafts):
            raise AssertionError(f"unexpected model call number {len(self.calls)}")
        return DraftResult(
            draft=self.drafts[len(self.calls) - 1], input_tokens=1200, output_tokens=640
        )


@pytest.fixture
def connection() -> duckdb.DuckDBPyConnection:
    database = build_database()
    run_model(database, publish_forward=False)
    run_variance(database)
    return database


@pytest.fixture
def prompts() -> PromptBundle:
    return load_prompts()


def _facts(connection: duckdb.DuckDBPyConnection, quarter: str) -> dict[str, Fact]:
    return {fact.key: fact for fact in quarter_facts(connection, quarter)}


def _memo(
    connection: duckdb.DuckDBPyConnection,
    quarter: str,
    *,
    deliveries: int | None = None,
    extra_sentences: tuple[str, ...] = (),
    extra_claims: tuple[Claim, ...] = (),
) -> NarrativeDraft:
    """A memo whose numbers come from the fact sheet, except a deliveries override."""
    facts = _facts(connection, quarter)
    shown = int(facts["actual.deliveries"].value) if deliveries is None else deliveries
    revenue = round(float(facts["actual.total_revenue"].value) / 1_000_000, 1)
    margin = round(float(facts["actual.gross_margin"].value), 1)
    sentences = [
        f"Deliveries were {shown:,} vehicles in {quarter}.",
        f"Total revenue was {revenue:,.1f} million dollars.",
        f"Gross margin was {margin:.1f} percent.",
        *extra_sentences,
    ]
    claims = [
        Claim(
            metric="actual.deliveries", period=quarter, value=shown, unit="units", sentence_ref="1"
        ),
        Claim(
            metric="actual.total_revenue",
            period=quarter,
            value=revenue,
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
        *extra_claims,
    ]
    return NarrativeDraft(memo=Memo(text=_text(sentences, 200), claims=claims), answers=[])


def _wrong_deliveries(connection: duckdb.DuckDBPyConnection, quarter: str, by: int) -> int:
    return int(_facts(connection, quarter)["actual.deliveries"].value) + by


def _stored(connection: duckdb.DuckDBPyConnection, quarter: str) -> tuple[bool, str]:
    row = connection.execute(
        "SELECT verified, payload FROM narrative WHERE quarter = ?", [quarter]
    ).fetchone()
    assert row is not None
    return bool(row[0]), row[1]


def test_wrong_first_draft_then_right_second_ends_verified(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    wrong = _wrong_deliveries(connection, QUARTER, 50_000)
    first = _memo(connection, QUARTER, deliveries=wrong)
    second = _memo(connection, QUARTER)
    client = ScriptedClient([first, second])

    out = narrate_and_review(
        connection, QUARTER, client, prompts=prompts, model=MODEL, with_questions=False
    )

    assert len(client.calls) == 2
    assert out.reasked is True
    assert out.review.clean
    assert out.first_review is not None
    assert out.first_review.counts["flagged"] == 1
    flagged = [item for item in out.first_review.results if item.result.status is Status.FLAGGED]
    assert flagged[0].location == "memo"
    assert flagged[0].result.expected == _facts(connection, QUARTER)["actual.deliveries"].value
    verified, payload = _stored(connection, QUARTER)
    assert verified is True
    assert NarrativeDraft.model_validate_json(payload) == second
    assert out.narration.input_hash == input_hash(client.calls[0].user, prompts, MODEL)
    assert (out.input_tokens, out.output_tokens) == (2400, 1280)


def test_both_drafts_wrong_keeps_the_flag_and_stores_unverified(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    first = _memo(connection, QUARTER, deliveries=_wrong_deliveries(connection, QUARTER, 50_000))
    second = _memo(connection, QUARTER, deliveries=_wrong_deliveries(connection, QUARTER, 70_000))
    client = ScriptedClient([first, second])

    out = narrate_and_review(
        connection, QUARTER, client, prompts=prompts, model=MODEL, with_questions=False
    )

    assert len(client.calls) == 2
    assert out.reasked is True
    assert out.review.counts["flagged"] == 1
    assert not out.review.clean
    verified, payload = _stored(connection, QUARTER)
    assert verified is False
    assert NarrativeDraft.model_validate_json(payload) == second


def test_clean_first_draft_is_not_re_asked(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    draft = _memo(connection, QUARTER)
    client = ScriptedClient([draft])

    out = narrate_and_review(
        connection, QUARTER, client, prompts=prompts, model=MODEL, with_questions=False
    )

    assert len(client.calls) == 1
    assert out.reasked is False
    assert out.first_review is None
    assert out.review.clean
    verified, _ = _stored(connection, QUARTER)
    assert verified is True


def test_unsupported_key_and_guard_phrase_trigger_a_re_ask_and_appear_in_the_correction(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    first = _memo(
        connection,
        QUARTER,
        extra_sentences=("The price target language is not part of this memo.",),
        extra_claims=(
            Claim(
                metric="actual.not_a_metric",
                period=QUARTER,
                value=5,
                unit="units",
                sentence_ref="1",
            ),
        ),
    )
    second = _memo(connection, QUARTER)
    client = ScriptedClient([first, second])

    out = narrate_and_review(
        connection, QUARTER, client, prompts=prompts, model=MODEL, with_questions=False
    )

    assert len(client.calls) == 2
    assert out.reasked is True
    assert out.review.clean
    assert out.first_review is not None
    assert out.first_review.counts["unsupported"] == 1
    assert [hit.phrase.lower() for hit in out.first_review.guard_hits] == ["price target"]

    sent = client.calls[1].user
    assert sent.startswith(client.calls[0].user + CORRECTIONS)
    correction = sent[len(client.calls[0].user + CORRECTIONS) :]
    assert correction == correction_message(out.first_review)
    assert (
        "In memo, sentence 1: actual.not_a_metric for 2024-Q1 is not on the fact sheet; "
        "use only listed keys and periods."
    ) in correction
    assert "In memo, remove the phrase 'price target'." in correction
    assert correction.endswith(
        "Return the full corrected JSON. Keep every other sentence unchanged."
    )


def test_cached_verified_narration_makes_no_call_and_no_re_ask(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    first_client = ScriptedClient([_memo(connection, QUARTER)])
    first = narrate_and_review(
        connection, QUARTER, first_client, prompts=prompts, model=MODEL, with_questions=False
    )
    assert first.review.clean

    client = ScriptedClient([])
    again = narrate_and_review(
        connection, QUARTER, client, prompts=prompts, model=MODEL, with_questions=False
    )

    assert client.calls == []
    assert again.narration.cached is True
    assert again.reasked is False
    assert again.first_review is None
    assert again.review.clean
    assert (again.input_tokens, again.output_tokens) == (0, 0)
    assert again.narration.draft == first.narration.draft


def test_no_path_replaces_the_models_number_with_the_fact_value(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    wrong_once = _wrong_deliveries(connection, QUARTER, 50_000)
    wrong_twice = _wrong_deliveries(connection, QUARTER, 70_000)
    first = _memo(connection, QUARTER, deliveries=wrong_once)
    second = _memo(connection, QUARTER, deliveries=wrong_twice)
    client = ScriptedClient([first, second])

    out = narrate_and_review(
        connection, QUARTER, client, prompts=prompts, model=MODEL, with_questions=False
    )

    fact_value = _facts(connection, QUARTER)["actual.deliveries"].value
    final_claim = out.narration.draft.memo.claims[0]
    assert final_claim.metric == "actual.deliveries"
    assert final_claim.value == wrong_twice
    assert out.narration.draft == second
    assert out.review.results[0].result.claim.value == wrong_twice
    assert out.review.results[0].result.expected == fact_value
    assert fact_value != Decimal(wrong_twice)
    _, payload = _stored(connection, QUARTER)
    assert NarrativeDraft.model_validate_json(payload).memo.claims[0].value == wrong_twice
    assert out.first_review is not None
    assert out.first_review.results[0].result.claim.value == wrong_once


def test_correction_names_the_model_value_and_the_fact_sheet_value(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    wrong = _wrong_deliveries(connection, QUARTER, 50_000)
    first = _memo(connection, QUARTER, deliveries=wrong)
    client = ScriptedClient([first, _memo(connection, QUARTER)])

    out = narrate_and_review(
        connection, QUARTER, client, prompts=prompts, model=MODEL, with_questions=False
    )

    fact_value = int(_facts(connection, QUARTER)["actual.deliveries"].value)
    assert out.first_review is not None
    assert correction_message(out.first_review).splitlines()[0] == (
        f"In memo, sentence 1: you wrote {wrong} units for actual.deliveries ({QUARTER}); "
        f"the fact sheet value is {fact_value} units."
    )


def test_latest_quarter_verifies_backtest_claims_from_the_backtest_sheet(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    average = next(
        fact for fact in backtest_facts(connection) if fact.key.endswith(".average_abs_pct_error")
    )
    claim = Claim(
        metric=average.key,
        period=average.period,
        value=float(average.value),
        unit="percent",
        sentence_ref="1",
    )
    answers = [
        Answer(
            question_number=number,
            text=_text([f"Answer {number} draws on the sheet."], 80),
            claims=[claim] if number == 7 else [],
        )
        for number in range(1, 11)
    ]
    draft = _memo(connection, LATEST).model_copy(update={"answers": answers})
    client = ScriptedClient([draft])

    out = narrate_and_review(
        connection, LATEST, client, prompts=prompts, model=MODEL, with_questions=True
    )

    assert len(client.calls) == 1
    assert out.review.clean
    assert out.review.counts["verified"] == 4
    verified, _ = _stored(connection, LATEST)
    assert verified is True


def test_first_call_sends_the_same_system_and_user_text_as_narrate_quarter(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    reference = FakeClient()
    plain = narrate_quarter(
        connection, QUARTER, reference, prompts=prompts, model=MODEL, with_questions=False
    )
    client = ScriptedClient([_memo(connection, QUARTER)])

    out = narrate_and_review(
        connection, QUARTER, client, prompts=prompts, model=MODEL, with_questions=False
    )

    assert client.calls[0].system == reference.calls[0].system == prompts.memo_instructions
    assert client.calls[0].user == reference.calls[0].user
    assert client.calls[0].temperature == prompts.temperature
    assert out.narration.input_hash == plain.input_hash


def test_review_all_covers_the_same_quarters_as_narrate_all_and_verifies_each(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    client = FakeClient()
    reviewed = review_all(connection, client, prompts=prompts, model=MODEL)

    assert [item.narration.quarter for item in reviewed] == list(PUBLISHED)
    assert [item.narration.kind for item in reviewed] == ["memo"] * 11 + ["memo+qa"]
    assert len(client.calls) == len(PUBLISHED)
    assert all(item.review.clean and not item.reasked for item in reviewed)
    assert all(_stored(connection, item.narration.quarter)[0] for item in reviewed)


def test_review_draft_counts_and_clean_flag(connection: duckdb.DuckDBPyConnection) -> None:
    clean = review_draft(
        _memo(connection, QUARTER),
        quarter_facts(connection, QUARTER),
        quarter=QUARTER,
        latest=False,
    )
    assert clean.clean
    assert clean.counts == {"verified": 3, "flagged": 0, "unsupported": 0, "total": 3}
    assert clean.guard_hits == ()
    assert clean.issues == ()

    dirty = review_draft(
        _memo(connection, QUARTER, deliveries=_wrong_deliveries(connection, QUARTER, 1)),
        quarter_facts(connection, QUARTER),
        quarter=QUARTER,
        latest=False,
    )
    assert not dirty.clean
    assert dirty.counts["flagged"] == 1
    assert dirty.results[0].result.status is Status.FLAGGED
    assert dirty.results[0].location == "memo"
