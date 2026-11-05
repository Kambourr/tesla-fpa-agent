"""The one-command pipeline on the fixture database. No network and no OpenAI call.

``run_ingest`` is replaced by the synthetic fixture builder, and every narration
client is a ``FakeClient``. An autouse fixture makes any urllib request or any
OpenAI SDK client fail the test, and sets sentinel secrets so a leak shows up.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pytest

from agent import run as run_module
from agent.__main__ import main
from agent.deliveries import repo_root
from agent.model_stage import run_model, run_variance
from agent.narrate import NarrationError, narrate_all, store_narration
from agent.narrative import load_prompts
from agent.publish import STAGE_NAMES, PublishError, build_dashboard
from agent.publish_schema import Dashboard, RunMetadata
from agent.run import run_pipeline
from agent.settings import Settings
from agent.usage import estimate_cost
from pipeline_fixture import build_database
from test_narrate import LATEST, FakeClient

NOW = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)
SECRET_KEY = "SENTINEL-KEY-VALUE-0123456789"
SECRET_AGENT = "pipeline-test-agent-sentinel"
CORRECTIONS = "\n\nCorrections needed:\n"


@pytest.fixture(autouse=True)
def _offline(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("the test tried to reach the network or OpenAI")

    monkeypatch.setattr("urllib.request.urlopen", refuse)
    monkeypatch.setattr("agent.narrate.OpenAI", refuse)
    monkeypatch.setenv("OPENAI_API_KEY", SECRET_KEY)
    monkeypatch.setenv("SEC_USER_AGENT", SECRET_AGENT)


def _fake_ingest(
    monkeypatch: pytest.MonkeyPatch,
    mutate: Callable[[duckdb.DuckDBPyConnection], None] | None = None,
) -> None:
    """Build the fixture database where ingest would put it, optionally changed first."""

    def ingest(
        *,
        database: Path,
        csv_path: Path | None = None,
        fixtures: Path | None = None,
    ) -> None:
        connection = build_database(str(database))
        try:
            if mutate is not None:
                mutate(connection)
        finally:
            connection.close()

    monkeypatch.setattr(run_module, "run_ingest", ingest)


def _run(
    tmp_path: Path,
    *,
    name: str,
    client: FakeClient | None = None,
    cache: Path | None = None,
    force: bool = False,
) -> tuple[RunMetadata, Path]:
    database = tmp_path / f"{name}.duckdb"
    output = tmp_path / f"{name}.dashboard.json"
    run = run_pipeline(
        database=database,
        output=output,
        fixtures=tmp_path,
        client=client,
        force=force,
        now=NOW,
        cache_path=cache,
    )
    return run, output


def _dashboard(output: Path) -> Dashboard:
    return Dashboard.model_validate_json(output.read_text(encoding="utf-8"))


def _quarter_of(user: str) -> str:
    """The quarter named in a user message, even when a correction block follows the JSON."""
    return str(json.loads(user.split(CORRECTIONS)[0])["quarter"])


def test_fixture_run_completes_every_stage_and_writes_a_valid_dashboard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_ingest(monkeypatch)
    client = FakeClient()
    run, output = _run(tmp_path, name="fpa", client=client)

    assert [stage.name for stage in run.stages] == list(STAGE_NAMES)
    assert all(stage.seconds is not None and stage.seconds >= 0 for stage in run.stages)
    assert sum(stage.seconds or 0 for stage in run.stages) <= run.duration_seconds + 0.001

    dashboard = _dashboard(output)
    assert len(dashboard.quarters) == 12
    assert dashboard.latest_quarter == LATEST
    assert dashboard.run.stages == run.stages
    assert len(client.calls) >= 12


def test_run_records_tokens_cost_and_data_as_of(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_ingest(monkeypatch)
    client = FakeClient()
    run, output = _run(tmp_path, name="fpa", client=client)

    model = Settings().openai_model
    assert run.model == model
    assert run.input_tokens == 1200 * len(client.calls)
    assert run.output_tokens == 640 * len(client.calls)
    assert run.estimated_cost_usd == estimate_cost(model, run.input_tokens, run.output_tokens)
    assert run.estimated_cost_usd is not None and run.estimated_cost_usd > 0
    dashboard = _dashboard(output)
    latest = next(item for item in dashboard.quarters if item.quarter == LATEST)
    assert latest.filing is not None
    assert run.data_as_of == latest.filing.filing_date
    assert run.started_at == NOW.isoformat(timespec="seconds")


def test_memo_claims_carry_the_verification_statuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_ingest(monkeypatch)
    _, output = _run(tmp_path, name="fpa", client=FakeClient())
    dashboard = _dashboard(output)

    for item in dashboard.quarters:
        assert item.memo is not None, item.quarter
        assert item.memo.verification.total == len(item.memo.claims)
        assert {claim.status for claim in item.memo.claims} <= {
            "verified",
            "flagged",
            "unsupported",
        }
        assert item.memo.claims, item.quarter

    database = tmp_path / "fpa.duckdb"
    connection = duckdb.connect(str(database), read_only=True)
    try:
        stored = json.loads(
            connection.execute(
                "SELECT claims FROM verification WHERE quarter = ?", [LATEST]
            ).fetchone()[0]
        )
    finally:
        connection.close()
    stored_memo = [(c["metric"], c["status"]) for c in stored if c["location"] == "memo"]
    latest = next(item for item in dashboard.quarters if item.quarter == LATEST)
    assert latest.memo is not None
    assert [(c.metric, c.status) for c in latest.memo.claims] == stored_memo


def test_qa_has_ten_answers_for_the_latest_quarter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_ingest(monkeypatch)
    _, output = _run(tmp_path, name="fpa", client=FakeClient())
    dashboard = _dashboard(output)

    assert dashboard.qa is not None
    assert dashboard.qa.quarter == LATEST
    assert [answer.number for answer in dashboard.qa.answers] == list(range(1, 11))
    questions = {question.number: question.text for question in load_prompts().questions}
    assert all(answer.question == questions[answer.number] for answer in dashboard.qa.answers)
    claims = sum(len(answer.claims) for answer in dashboard.qa.answers)
    assert dashboard.qa.verification.total == claims
    earlier = [item for item in dashboard.quarters if item.quarter != LATEST]
    assert all(item.memo is not None for item in earlier)


def test_second_run_with_the_same_cache_makes_no_calls_and_publishes_the_same_memos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_ingest(monkeypatch)
    cache = tmp_path / "narrative_cache.json"
    first_client = FakeClient()
    _, first_output = _run(tmp_path, name="first", client=first_client, cache=cache)
    assert cache.is_file()

    second_client = FakeClient()
    _, second_output = _run(tmp_path, name="second", client=second_client, cache=cache)

    assert second_client.calls == []
    first = _dashboard(first_output)
    second = _dashboard(second_output)
    assert [item.memo and item.memo.text for item in second.quarters] == [
        item.memo and item.memo.text for item in first.quarters
    ]
    assert second.qa == first.qa


def test_changed_fact_sheet_regenerates_only_that_quarter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = tmp_path / "narrative_cache.json"
    _fake_ingest(monkeypatch)
    _, first_output = _run(tmp_path, name="first", client=FakeClient(), cache=cache)

    def restate(connection: duckdb.DuckDBPyConnection) -> None:
        # Move $1M into services, which feeds revenue, gross profit and operating
        # income, so the bridges still tie. The latest quarter is changed because
        # no later quarter's forecast reads it, so only its own narrative changes.
        for metric in ("services_and_other", "total_revenue", "gross_profit", "operating_income"):
            connection.execute(
                "UPDATE quarter_actual SET value = value + 1000000 "
                "WHERE quarter = ? AND metric = ?",
                [LATEST, metric],
            )

    _fake_ingest(monkeypatch, mutate=restate)
    client = FakeClient()
    _, second_output = _run(tmp_path, name="second", client=client, cache=cache)

    assert {_quarter_of(call.user) for call in client.calls} == {LATEST}
    first = _dashboard(first_output)
    second = _dashboard(second_output)
    for before, after in zip(first.quarters, second.quarters, strict=True):
        if before.quarter != LATEST:
            assert before.memo and after.memo and before.memo.text == after.memo.text
        else:
            assert before.memo and after.memo and before.memo.text != after.memo.text


def test_force_calls_the_model_even_when_a_verified_narrative_is_cached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_ingest(monkeypatch)
    cache = tmp_path / "narrative_cache.json"
    _run(tmp_path, name="first", client=FakeClient(), cache=cache)

    client = FakeClient()
    _run(tmp_path, name="forced", client=client, cache=cache, force=True)
    assert len(client.calls) >= 12


def test_publishing_a_narrative_without_a_verification_row_is_a_clear_error() -> None:
    connection = build_database()
    try:
        run_model(connection, publish_forward=False)
        run_variance(connection)
        prompts = load_prompts()
        results = narrate_all(connection, FakeClient(), prompts=prompts, model="test-model")
        for result in results:
            store_narration(connection, result, prompts, "test-model")
        with pytest.raises(PublishError, match="python -m agent verify"):
            build_dashboard(connection)
    finally:
        connection.close()


def test_cli_run_prints_each_stage_and_the_usage_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _fake_ingest(monkeypatch)
    monkeypatch.setattr(run_module, "OpenAIClient", FakeClient)
    code = main(
        [
            "run",
            "--database",
            str(tmp_path / "fpa.duckdb"),
            "--output",
            str(tmp_path / "dashboard.json"),
            "--fixtures",
            str(tmp_path),
        ]
    )
    text = capsys.readouterr().out
    assert code == 0
    for name in STAGE_NAMES:
        assert f"stage {name}: " in text
    assert "narration used" in text
    assert "run wrote" in text


def test_no_secret_reaches_the_printed_output_or_the_dashboard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _fake_ingest(monkeypatch)
    monkeypatch.setattr(run_module, "OpenAIClient", FakeClient)
    output = tmp_path / "dashboard.json"
    code = main(
        [
            "run",
            "--database",
            str(tmp_path / "fpa.duckdb"),
            "--output",
            str(output),
            "--fixtures",
            str(tmp_path),
        ]
    )
    printed = capsys.readouterr()
    assert code == 0
    for text in (printed.out, printed.err, output.read_text(encoding="utf-8")):
        assert SECRET_KEY not in text
        assert SECRET_AGENT not in text


def test_fixture_run_without_explicit_paths_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["run", "--fixtures", str(tmp_path)]) == 1
    assert "--database and --output" in capsys.readouterr().err
    assert not (tmp_path / "fpa.duckdb").exists()


def test_live_run_without_a_key_stops_before_narration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_ingest(monkeypatch)
    monkeypatch.delenv("OPENAI_API_KEY")
    with pytest.raises(NarrationError, match="OPENAI_API_KEY is not set"):
        run_pipeline(
            database=tmp_path / "fpa.duckdb",
            output=tmp_path / "dashboard.json",
            fixtures=tmp_path,
            now=NOW,
        )
    assert not (tmp_path / "dashboard.json").exists()


@pytest.mark.skipif(shutil.which("make") is None, reason="make is not installed")
def test_make_run_prints_the_pipeline_command() -> None:
    result = subprocess.run(
        ["make", "-n", "run"],
        cwd=repo_root(),
        capture_output=True,
        text=True,
        check=True,
    )
    assert "python -m agent run" in result.stdout
