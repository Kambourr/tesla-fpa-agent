"""Run every stage in order with one call: ``python -m agent run``.

Each stage is timed with ``time.perf_counter()`` into one of the six published
names: ``ingest`` (``run_ingest``), ``load`` (schema check on the database),
``forecast`` (``run_model`` and ``run_variance``), ``explain`` (narration with
at most one re-ask, ``review_all``), ``verify`` (``verify_all``, then the
narrative cache export) and ``publish`` (``build_dashboard``, then the file).
The file write comes after the publish timing, so ``publish`` does not include it.

The narration client defaults to ``OpenAIClient()``, which needs
``OPENAI_API_KEY``. Tests pass a fake. The narrative cache is imported before
``explain`` and exported after ``verify``. With ``fixtures`` set and no
``cache_path``, the cache is skipped, so numbers from a fixture never reach the
committed ``data/narrative_cache.json``.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeVar

import duckdb

from agent.ingest import run_ingest
from agent.model_stage import StageError, run_model, run_variance
from agent.narrate import NarrationClient, OpenAIClient
from agent.narrative_store import CACHE_PATH, export_verified, import_cache
from agent.publish import STAGE_NAMES, build_dashboard, write_dashboard
from agent.publish_schema import Dashboard, RunMetadata, Stage, StageName
from agent.review import ReviewedNarration, review_all
from agent.schema import apply_schema
from agent.settings import Settings
from agent.usage import RunUsage, log_usage, summarize_usage
from agent.verify_stage import VerificationReport, verify_all

T = TypeVar("T")


@dataclass(frozen=True)
class _Usage:
    """The three fields ``summarize_usage`` reads from one narration result."""

    input_tokens: int
    output_tokens: int
    cached: bool


class _Timings:
    def __init__(self) -> None:
        self.seconds: dict[str, float] = {}

    def run(self, name: StageName, action: Callable[[], T]) -> T:
        began = time.perf_counter()
        try:
            return action()
        finally:
            self.seconds[name] = round(time.perf_counter() - began, 4)


def run_pipeline(
    *,
    database: Path,
    output: Path,
    fixtures: Path | None = None,
    client: NarrationClient | None = None,
    force: bool = False,
    now: datetime | None = None,
    cache_path: Path | None = None,
) -> RunMetadata:
    """Run ingest through publish and return the run's metadata. Writes ``output``.

    ``force`` regenerates every narrative, including verified cached ones.
    ``now`` fixes ``started_at`` and the dashboard's ``generated_at``, for tests.
    """
    started = datetime.now(UTC) if now is None else now.astimezone(UTC)
    cache = _cache_path(fixtures, cache_path)
    model = Settings().openai_model
    timings = _Timings()
    began = time.perf_counter()

    timings.run("ingest", lambda: run_ingest(database=database, fixtures=fixtures))
    connection = duckdb.connect(str(database))
    try:
        timings.run("load", lambda: _load_check(connection))
        timings.run("forecast", lambda: _forecast(connection))
        reviewed = timings.run(
            "explain",
            lambda: _explain(connection, client, model, force=force, cache=cache),
        )
        timings.run("verify", lambda: _verify(connection, cache))
        dashboard = timings.run("publish", lambda: build_dashboard(connection, now=started))
    finally:
        connection.close()

    usage = _usage(reviewed, model)
    log_usage(usage)
    run = RunMetadata(
        started_at=started.isoformat(timespec="seconds"),
        duration_seconds=round(time.perf_counter() - began, 4),
        stages=[Stage(name=name, seconds=timings.seconds[name]) for name in STAGE_NAMES],
        model=model,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        estimated_cost_usd=usage.estimated_cost_usd,
        data_as_of=_data_as_of(dashboard),
    )
    write_dashboard(dashboard.model_copy(update={"run": run}), output)
    return run


def _cache_path(fixtures: Path | None, cache_path: Path | None) -> Path | None:
    if cache_path is not None:
        return cache_path
    return None if fixtures is not None else CACHE_PATH


def _load_check(connection: duckdb.DuckDBPyConnection) -> int:
    """Apply the SQL schema to the loaded database and count the stored actuals."""
    apply_schema(connection)
    found = connection.execute("SELECT count(*) FROM quarter_actual").fetchone()
    return int(found[0]) if found is not None else 0


def _forecast(connection: duckdb.DuckDBPyConnection) -> None:
    run_model(connection, publish_forward=Settings().publish_forward_forecast)
    variance = run_variance(connection)
    if variance.failures:
        raise StageError("bridges not written: " + "; ".join(variance.failures))


def _explain(
    connection: duckdb.DuckDBPyConnection,
    client: NarrationClient | None,
    model: str,
    *,
    force: bool,
    cache: Path | None,
) -> list[ReviewedNarration]:
    if cache is not None:
        import_cache(connection, cache)
    chosen = OpenAIClient() if client is None else client
    return review_all(connection, chosen, model=model, force=force)


def _verify(connection: duckdb.DuckDBPyConnection, cache: Path | None) -> list[VerificationReport]:
    reports = verify_all(connection)
    if cache is not None:
        export_verified(connection, cache)
    return reports


def _usage(reviewed: list[ReviewedNarration], model: str) -> RunUsage:
    """Token totals over every model call, re-asks included. Calls count each draft sent."""
    usage = summarize_usage(
        [_Usage(item.input_tokens, item.output_tokens, item.narration.cached) for item in reviewed],
        model,
    )
    calls = sum(1 for item in reviewed if not item.narration.cached) + sum(
        1 for item in reviewed if item.reasked
    )
    return replace(usage, calls=calls)


def _data_as_of(dashboard: Dashboard) -> str | None:
    for quarter in dashboard.quarters:
        if quarter.quarter == dashboard.latest_quarter and quarter.filing is not None:
            return quarter.filing.filing_date
    return None
