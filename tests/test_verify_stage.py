"""The verification report, restatements, and the narrate and verify commands.

Fixture database and fake clients only. No test reaches OpenAI or the network.
The CLI tests run with no OPENAI_API_KEY in the environment.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest

from agent.actuals import ReportedFact, assemble_quarter_actuals, store_reported_facts
from agent.fact_sheet import quarter_facts
from agent.model_stage import StageError, run_model, run_variance
from agent.narrative import PromptBundle, load_prompts
from agent.review import narrate_and_review, review_all
from agent.verifier import Status
from agent.verify_stage import format_report, restatements, verify_all, verify_quarter
from pipeline_fixture import build_database
from test_narrate import LATEST, PUBLISHED, FakeClient
from test_review import ScriptedClient, _memo, _wrong_deliveries

REPO_ROOT = Path(__file__).resolve().parents[1]
QUARTER = "2024-Q1"
RESTATED = "2024-Q2"
MODEL = "test-model"


@pytest.fixture
def connection() -> duckdb.DuckDBPyConnection:
    database = build_database()
    run_model(database, publish_forward=False)
    run_variance(database)
    return database


@pytest.fixture
def prompts() -> PromptBundle:
    return load_prompts()


def _narrate(
    connection: duckdb.DuckDBPyConnection,
    quarter: str,
    drafts: list,
    prompts: PromptBundle,
    *,
    force: bool = False,
) -> None:
    narrate_and_review(
        connection,
        quarter,
        ScriptedClient(drafts),
        prompts=prompts,
        model=MODEL,
        with_questions=False,
        force=force,
    )


def _fact_value(connection: duckdb.DuckDBPyConnection, quarter: str, key: str) -> Decimal:
    return {fact.key: fact for fact in quarter_facts(connection, quarter)}[key].value


def _verification_row(connection: duckdb.DuckDBPyConnection, quarter: str) -> tuple:
    row = connection.execute(
        """
        SELECT verified, flagged, unsupported, total, guard_hits, reasked
        FROM verification WHERE quarter = ?
        """,
        [quarter],
    ).fetchone()
    assert row is not None
    return row


def test_counts_match_a_scripted_draft_with_one_flagged_claim(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    wrong = _wrong_deliveries(connection, QUARTER, 50_000)
    _narrate(
        connection,
        QUARTER,
        [
            _memo(connection, QUARTER, deliveries=wrong),
            _memo(connection, QUARTER, deliveries=wrong),
        ],
        prompts,
    )

    report = verify_quarter(connection, QUARTER, latest=False)

    assert (report.verified, report.flagged, report.unsupported, report.total) == (2, 1, 0, 3)
    assert report.guard_hits == ()
    assert report.issues == ()
    flagged = [item for item in report.results if item.result.status is Status.FLAGGED]
    assert len(flagged) == 1
    assert flagged[0].location == "memo"
    assert flagged[0].result.claim.value == wrong
    assert flagged[0].result.expected == _fact_value(connection, QUARTER, "actual.deliveries")
    assert _verification_row(connection, QUARTER)[:4] == (2, 1, 0, 3)


def test_guard_hit_is_recorded_in_the_report_and_the_row(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    guarded = _memo(
        connection,
        QUARTER,
        extra_sentences=("We recommend this stock to long-term holders.",),
    )
    _narrate(connection, QUARTER, [guarded, guarded], prompts)

    report = verify_quarter(connection, QUARTER, latest=False)

    assert [(hit.text_kind, hit.phrase.lower()) for hit in report.guard_hits] == [
        ("memo", "we recommend")
    ]
    assert report.flagged == 0
    stored = _verification_row(connection, QUARTER)
    assert "we recommend" in stored[4].lower()
    assert "keyword guard 1 hit" in format_report(report)


def test_verification_row_is_written_then_replaced_on_rerun(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    _narrate(connection, QUARTER, [_memo(connection, QUARTER)], prompts)
    verify_quarter(connection, QUARTER, latest=False)
    assert _verification_row(connection, QUARTER)[:3] == (3, 0, 0)

    wrong = _wrong_deliveries(connection, QUARTER, 50_000)
    _narrate(
        connection,
        QUARTER,
        [
            _memo(connection, QUARTER, deliveries=wrong),
            _memo(connection, QUARTER, deliveries=wrong),
        ],
        prompts,
        force=True,
    )
    verify_quarter(connection, QUARTER, latest=False)

    rows = connection.execute("SELECT count(*) FROM verification").fetchone()
    assert rows == (1,)
    assert _verification_row(connection, QUARTER)[:3] == (2, 1, 0)


def test_missing_narration_raises_a_clear_error(connection: duckdb.DuckDBPyConnection) -> None:
    with pytest.raises(StageError, match=QUARTER) as single:
        verify_quarter(connection, QUARTER, latest=False)
    assert "python -m agent narrate" in str(single.value)

    with pytest.raises(StageError, match="python -m agent narrate"):
        verify_all(connection)
    assert connection.execute("SELECT count(*) FROM verification").fetchone() == (0,)


def test_later_filing_restatement_is_reported_and_first_value_is_kept(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    first = _first_value(connection, RESTATED, "total_revenue")
    gross = _first_value(connection, RESTATED, "gross_profit")
    later_revenue = ReportedFact(
        metric="total_revenue",
        period_start=date(2024, 4, 1),
        period_end=date(2024, 6, 30),
        accession="0000000002-25-000001",
        form="10-Q",
        filing_period_end=date(2025, 6, 30),
        filing_date=date(2025, 7, 25),
        filing_url="https://example.com/0000000002-25-000001",
        value=first + 1_000_000,
        unit="USD",
        concept="fixture",
    )
    # A later comparative with the same value is not a restatement.
    later_gross = ReportedFact(
        metric="gross_profit",
        period_start=date(2024, 4, 1),
        period_end=date(2024, 6, 30),
        accession="0000000002-25-000002",
        form="10-Q",
        filing_period_end=date(2025, 6, 30),
        filing_date=date(2025, 7, 25),
        filing_url="https://example.com/0000000002-25-000002",
        value=gross,
        unit="USD",
        concept="fixture",
    )
    store_reported_facts(connection, [later_revenue, later_gross])
    assemble_quarter_actuals(connection)

    assert _first_value(connection, RESTATED, "total_revenue") == first
    fact_rows = connection.execute(
        "SELECT count(*) FROM fact WHERE metric = 'total_revenue' AND period_start = ?",
        [date(2024, 4, 1)],
    ).fetchone()
    assert fact_rows == (2,)

    expected = [
        {
            "metric": "total_revenue",
            "first_reported": first,
            "later_value": first + 1_000_000,
            "later_accession": "0000000002-25-000001",
            "later_filing_date": date(2025, 7, 25),
        }
    ]
    assert restatements(connection, RESTATED) == expected

    _narrate(connection, RESTATED, [_memo(connection, RESTATED)], prompts)
    report = verify_quarter(connection, RESTATED, latest=False)
    assert list(report.restatements) == expected
    text = format_report(report)
    assert "1 later restatement noted (total_revenue)" in text
    assert "Actuals keep the first-reported value." in text


def test_verify_all_reports_every_published_quarter(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    review_all(connection, FakeClient())

    reports = verify_all(connection)

    assert [report.quarter for report in reports] == list(PUBLISHED)
    assert reports[-1].quarter == LATEST
    assert [report.latest for report in reports] == [q == LATEST for q in PUBLISHED]
    assert all(report.flagged == 0 and report.unsupported == 0 for report in reports)
    assert connection.execute("SELECT count(*) FROM verification").fetchone() == (12,)
    assert format_report(reports[-1]).startswith(
        f"{LATEST}: 3 of 3 figures verified, 0 flagged, 0 unsupported; "
        "keyword guard clean; no later restatements."
    )


def test_cli_narrate_without_a_key_exits_1_and_prints_no_key(tmp_path: Path) -> None:
    database = tmp_path / "fpa.duckdb"
    build_database(str(database)).close()
    completed = _run_cli(tmp_path, "narrate", database)

    assert completed.returncode == 1
    assert "OPENAI_API_KEY is not set" in completed.stderr
    assert completed.stdout == ""


def test_cli_verify_prints_the_summary_for_stored_narrations(tmp_path: Path) -> None:
    database = tmp_path / "fpa.duckdb"
    connection = build_database(str(database))
    run_model(connection, publish_forward=False)
    run_variance(connection)
    review_all(connection, FakeClient())
    connection.close()

    completed = _run_cli(tmp_path, "verify", database)

    assert completed.returncode == 0, completed.stderr
    summaries = [line for line in completed.stdout.splitlines() if "figures verified" in line]
    assert len(summaries) == len(PUBLISHED)
    assert summaries[0].startswith("2023-Q4: 3 of 3 figures verified, 0 flagged, 0 unsupported;")
    assert summaries[-1].startswith(f"{LATEST}: 3 of 3 figures verified")
    assert "OPENAI_API_KEY" not in completed.stdout + completed.stderr


def test_cli_verify_fails_without_a_database(tmp_path: Path) -> None:
    completed = _run_cli(tmp_path, "verify", tmp_path / "none.duckdb")

    assert completed.returncode == 1
    assert "Run `python -m agent ingest` first" in completed.stderr


def _first_value(connection: duckdb.DuckDBPyConnection, quarter: str, metric: str) -> Decimal:
    row = connection.execute(
        "SELECT value FROM quarter_actual WHERE quarter = ? AND metric = ?",
        [quarter, metric],
    ).fetchone()
    assert row is not None
    return Decimal(row[0])


def _run_cli(cwd: Path, command: str, database: Path) -> subprocess.CompletedProcess[str]:
    """Run `python -m agent` with OPENAI_API_KEY removed from the environment."""
    environment = {key: value for key, value in os.environ.items() if key != "OPENAI_API_KEY"}
    environment["PYTHONPATH"] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, "-m", "agent", command, "--database", str(database)],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=environment,
        check=False,
    )
