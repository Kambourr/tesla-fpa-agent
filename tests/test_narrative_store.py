"""The narrative cache file: export of verified rows, import into a fresh database.

Every client is a ``FakeClient`` or a ``NoCalls`` that fails on any call.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from agent.model_stage import run_model, run_variance
from agent.narrate import DraftResult, NarrationResult, mark_verified, narrate_all, store_narration
from agent.narrative import PromptBundle, load_prompts
from agent.narrative_store import NarrativeCacheError, export_verified, import_cache
from pipeline_fixture import build_database
from test_narrate import LATEST, PUBLISHED, FakeClient

MODEL = "test-model"
SECRET = "SENTINEL-KEY-VALUE-CACHE-0987654321"
FIELDS = {
    "quarter",
    "kind",
    "input_hash",
    "prompt_version",
    "model",
    "payload",
    "input_tokens",
    "output_tokens",
    "issues",
}


class NoCalls:
    def draft(self, **kwargs: object) -> DraftResult:
        raise AssertionError("the model was called")


@pytest.fixture
def prompts() -> PromptBundle:
    return load_prompts()


def _narrated(prompts: PromptBundle, *, verified: bool) -> duckdb.DuckDBPyConnection:
    connection = build_database()
    run_model(connection, publish_forward=False)
    run_variance(connection)
    results: list[NarrationResult] = narrate_all(
        connection, FakeClient(), prompts=prompts, model=MODEL
    )
    for result in results:
        store_narration(connection, result, prompts, MODEL)
        if verified:
            mark_verified(connection, result.quarter, result.input_hash)
    return connection


def test_export_writes_every_verified_row_sorted_with_the_listed_fields(
    tmp_path: Path, prompts: PromptBundle
) -> None:
    connection = _narrated(prompts, verified=True)
    path = tmp_path / "cache.json"
    assert export_verified(connection, path) == len(PUBLISHED)

    entries = json.loads(path.read_text(encoding="utf-8"))
    assert [entry["quarter"] for entry in entries] == list(PUBLISHED)
    assert all(set(entry) == FIELDS for entry in entries)
    assert entries[-1]["kind"] == "memo+qa"
    assert entries[0]["kind"] == "memo"
    assert all(entry["model"] == MODEL for entry in entries)


def test_export_is_stable_byte_for_byte(tmp_path: Path, prompts: PromptBundle) -> None:
    connection = _narrated(prompts, verified=True)
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    export_verified(connection, first)
    export_verified(connection, second)
    assert first.read_bytes() == second.read_bytes()


def test_export_leaves_out_unverified_rows(tmp_path: Path, prompts: PromptBundle) -> None:
    connection = _narrated(prompts, verified=False)
    path = tmp_path / "cache.json"
    assert export_verified(connection, path) == 0
    assert json.loads(path.read_text(encoding="utf-8")) == []


def test_import_into_a_fresh_database_makes_the_next_narration_a_cache_hit(
    tmp_path: Path, prompts: PromptBundle
) -> None:
    source = _narrated(prompts, verified=True)
    path = tmp_path / "cache.json"
    export_verified(source, path)

    fresh = build_database()
    run_model(fresh, publish_forward=False)
    run_variance(fresh)
    assert import_cache(fresh, path) == len(PUBLISHED)
    verified = fresh.execute("SELECT count(*) FROM narrative WHERE verified").fetchone()
    assert verified is not None and verified[0] == len(PUBLISHED)

    results = narrate_all(fresh, NoCalls(), prompts=prompts, model=MODEL)
    assert all(result.cached for result in results)
    assert [result.quarter for result in results] == list(PUBLISHED)


def test_import_without_a_file_changes_nothing(tmp_path: Path, prompts: PromptBundle) -> None:
    connection = _narrated(prompts, verified=False)
    assert import_cache(connection, tmp_path / "missing.json") == 0
    verified = connection.execute("SELECT count(*) FROM narrative WHERE verified").fetchone()
    assert verified is not None and verified[0] == 0


def test_a_malformed_file_is_refused_and_writes_nothing(
    tmp_path: Path, prompts: PromptBundle
) -> None:
    source = _narrated(prompts, verified=True)
    path = tmp_path / "cache.json"
    export_verified(source, path)
    entries = json.loads(path.read_text(encoding="utf-8"))
    entries[-1]["payload"] = {"memo": {"text": "x"}}
    path.write_text(json.dumps(entries), encoding="utf-8")

    fresh = build_database()
    run_model(fresh, publish_forward=False)
    run_variance(fresh)
    with pytest.raises(NarrativeCacheError, match="not a valid narrative"):
        import_cache(fresh, path)
    verified = fresh.execute("SELECT count(*) FROM narrative WHERE verified").fetchone()
    assert verified is not None and verified[0] == 0


@pytest.mark.parametrize(
    "text, message",
    [
        ("{not json", "not valid JSON"),
        ('{"quarter": "2026-Q3"}', "must hold a list"),
        ('[{"quarter": "2026-Q3"}]', "missing a field"),
    ],
)
def test_unreadable_files_are_refused(tmp_path: Path, text: str, message: str) -> None:
    path = tmp_path / "cache.json"
    path.write_text(text, encoding="utf-8")
    connection = build_database()
    with pytest.raises(NarrativeCacheError, match=message):
        import_cache(connection, path)


def test_the_cache_file_holds_no_secret(
    tmp_path: Path, prompts: PromptBundle, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", SECRET)
    connection = _narrated(prompts, verified=True)
    path = tmp_path / "cache.json"
    export_verified(connection, path)
    assert SECRET not in path.read_text(encoding="utf-8")
    assert LATEST in path.read_text(encoding="utf-8")
