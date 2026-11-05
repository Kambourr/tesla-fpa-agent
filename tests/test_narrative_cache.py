"""The verified narrative cache and the force flag, on the fixture database.

No network calls: every client is a ``FakeClient`` that counts its calls.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import duckdb
import pytest

from agent.model_stage import run_model, run_variance
from agent.narrate import (
    NarrationResult,
    mark_verified,
    narrate_all,
    narrate_quarter,
    store_narration,
)
from agent.narrative import PromptBundle, load_prompts
from agent.schema import SQL_DIR, apply_schema
from pipeline_fixture import build_database
from test_narrate import LATEST, PUBLISHED, FakeClient

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


def _run(
    connection: duckdb.DuckDBPyConnection,
    prompts: PromptBundle,
    *,
    model: str = MODEL,
    force: bool = False,
) -> tuple[list[NarrationResult], FakeClient]:
    client = FakeClient()
    results = narrate_all(connection, client, prompts=prompts, model=model, force=force)
    return results, client


def _store_verified(
    connection: duckdb.DuckDBPyConnection,
    results: list[NarrationResult],
    prompts: PromptBundle,
    model: str = MODEL,
) -> None:
    for result in results:
        store_narration(connection, result, prompts, model)
        mark_verified(connection, result.quarter, result.input_hash)


def _called_quarters(client: FakeClient) -> list[str]:
    return [json.loads(call.user)["quarter"] for call in client.calls]


def test_second_run_makes_no_client_calls_and_returns_the_same_drafts(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    first, first_client = _run(connection, prompts)
    assert _called_quarters(first_client) == list(PUBLISHED)
    assert all(not result.cached for result in first)
    _store_verified(connection, first, prompts)

    second, second_client = _run(connection, prompts)
    assert second_client.calls == []
    assert all(result.cached for result in second)
    assert [result.quarter for result in second] == list(PUBLISHED)
    assert [result.draft for result in second] == [result.draft for result in first]
    assert [result.issues for result in second] == [result.issues for result in first]
    assert [result.kind for result in second] == [result.kind for result in first]
    assert all((result.input_tokens, result.output_tokens) == (0, 0) for result in second)
    assert [result.input_hash for result in second] == [result.input_hash for result in first]


def test_changing_the_model_misses_every_quarter(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    first, _ = _run(connection, prompts, model="model-a")
    _store_verified(connection, first, prompts, model="model-a")

    results, client = _run(connection, prompts, model="model-b")
    assert _called_quarters(client) == list(PUBLISHED)
    assert all(not result.cached for result in results)


def test_changing_the_prompt_version_misses_every_quarter(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    first, _ = _run(connection, prompts)
    _store_verified(connection, first, prompts)

    newer = prompts.model_copy(update={"version": "2099-01-01.1"})
    results, client = _run(connection, newer)
    assert _called_quarters(client) == list(PUBLISHED)
    assert all(not result.cached for result in results)


def test_changing_one_actual_misses_only_that_quarter(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    first, _ = _run(connection, prompts)
    _store_verified(connection, first, prompts)

    connection.execute(
        "UPDATE quarter_actual SET value = value + 1000000 "
        "WHERE quarter = ? AND metric = 'total_revenue'",
        ["2025-Q2"],
    )
    run_variance(connection)

    results, client = _run(connection, prompts)
    assert _called_quarters(client) == ["2025-Q2"]
    hits = {result.quarter for result in results if result.cached}
    assert hits == set(PUBLISHED) - {"2025-Q2"}
    changed = next(result for result in results if result.quarter == "2025-Q2")
    assert changed.input_hash != next(r for r in first if r.quarter == "2025-Q2").input_hash


def test_force_calls_the_client_for_every_quarter_even_on_a_hit(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    first, _ = _run(connection, prompts)
    _store_verified(connection, first, prompts)

    results, client = _run(connection, prompts, force=True)
    assert _called_quarters(client) == list(PUBLISHED)
    assert all(not result.cached for result in results)


def test_forced_fresh_draft_is_unverified_until_marked(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    first, _ = _run(connection, prompts)
    _store_verified(connection, first, prompts)

    forced, _ = _run(connection, prompts, force=True)
    for result in forced:
        store_narration(connection, result, prompts, MODEL)

    again, client = _run(connection, prompts)
    assert _called_quarters(client) == list(PUBLISHED)
    assert all(not result.cached for result in again)


def test_cached_results_stay_verified_when_stored_again(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    first, _ = _run(connection, prompts)
    _store_verified(connection, first, prompts)

    cached, _ = _run(connection, prompts)
    for result in cached:
        store_narration(connection, result, prompts, MODEL)

    third, client = _run(connection, prompts)
    assert client.calls == []
    assert all(result.cached for result in third)


def test_unverified_stored_row_is_not_reused(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    first, _ = _run(connection, prompts)
    for result in first:
        store_narration(connection, result, prompts, MODEL)

    results, client = _run(connection, prompts)
    assert _called_quarters(client) == list(PUBLISHED)
    assert all(not result.cached for result in results)


def test_mark_verified_only_marks_the_row_with_that_hash(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    first, _ = _run(connection, prompts)
    result = next(r for r in first if r.quarter == LATEST)
    store_narration(connection, result, prompts, MODEL)

    mark_verified(connection, LATEST, "not-the-hash")
    assert _verified_flag(connection, LATEST) is False

    mark_verified(connection, LATEST, result.input_hash)
    assert _verified_flag(connection, LATEST) is True


def test_only_the_matching_quarter_is_reused_when_one_is_unverified(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    first, _ = _run(connection, prompts)
    _store_verified(connection, first, prompts)
    connection.execute("UPDATE narrative SET verified = FALSE WHERE quarter = ?", ["2024-Q2"])

    results, client = _run(connection, prompts)
    assert _called_quarters(client) == ["2024-Q2"]
    assert {result.quarter for result in results if not result.cached} == {"2024-Q2"}


def test_narrate_quarter_cache_hit_skips_the_client(
    connection: duckdb.DuckDBPyConnection, prompts: PromptBundle
) -> None:
    first = narrate_quarter(
        connection, LATEST, FakeClient(), prompts=prompts, model=MODEL, with_questions=True
    )
    store_narration(connection, first, prompts, MODEL)
    mark_verified(connection, LATEST, first.input_hash)

    client = FakeClient()
    hit = narrate_quarter(
        connection, LATEST, client, prompts=prompts, model=MODEL, with_questions=True
    )
    assert client.calls == []
    assert hit.cached is True
    assert hit.kind == "memo+qa"
    assert len(hit.draft.answers) == 10
    assert hit.draft == first.draft


def test_schema_migration_adds_verified_and_runs_twice(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    apply_schema(connection)
    apply_schema(connection)
    row = connection.execute(
        """
        SELECT is_nullable, column_default FROM information_schema.columns
        WHERE table_name = 'narrative' AND column_name = 'verified'
        """
    ).fetchone()
    assert row == ("NO", "false")


def test_migration_adds_verified_to_an_existing_table_with_rows(tmp_path: Path) -> None:
    for name in ("011_narrative.sql", "012_narrative_verified.sql"):
        shutil.copy(SQL_DIR / name, tmp_path / name)
    connection = duckdb.connect(":memory:")
    apply_schema(connection, sql_dir=tmp_path)
    connection.execute("DROP TABLE narrative")
    connection.execute((SQL_DIR / "011_narrative.sql").read_text(encoding="utf-8"))
    connection.execute(
        "INSERT INTO narrative VALUES ('2024-Q1', 'memo', 'h', 'v', 'm', '{}', 1, 1, '[]', now())"
    )

    apply_schema(connection, sql_dir=tmp_path)
    apply_schema(connection, sql_dir=tmp_path)
    assert connection.execute("SELECT quarter, verified FROM narrative").fetchall() == [
        ("2024-Q1", False)
    ]


def _verified_flag(connection: duckdb.DuckDBPyConnection, quarter: str) -> bool:
    row = connection.execute(
        "SELECT verified FROM narrative WHERE quarter = ?", [quarter]
    ).fetchone()
    assert row is not None
    return bool(row[0])
