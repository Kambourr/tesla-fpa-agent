"""`python -m agent <stage>` runs one pipeline stage.

`ingest` loads filings and deliveries. `--fixtures` reads local JSON, and the
default path uses the SEC cache. `model` writes forecasts, scenarios, and the
backtest. `variance` writes the four bridges. `narrate` drafts and checks the
memos and Q&A with OpenAI. `verify` writes the verification report per quarter.
`publish` writes the dashboard JSON the site reads. `run` executes every stage
in order and prints each stage's time. No command prints `SEC_USER_AGENT` or
`OPENAI_API_KEY`.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import duckdb

from agent.deliveries import default_csv_path
from agent.ingest import IngestError, default_database_path, run_ingest
from agent.model_stage import StageError, run_model, run_variance
from agent.narrate import NarrationError, OpenAIClient
from agent.publish import STAGE_NAMES, PublishError, build_dashboard, write_dashboard
from agent.publish_schema import RunMetadata, Stage
from agent.review import ReviewedNarration, review_all
from agent.run import run_pipeline
from agent.schema import apply_schema
from agent.sec import MissingUserAgentError
from agent.settings import Settings
from agent.verify_stage import format_report, verify_all

DASHBOARD_PATH = Path(__file__).resolve().parents[1] / "site" / "public" / "data" / "dashboard.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agent")
    subcommands = parser.add_subparsers(dest="command", required=True)
    ingest = subcommands.add_parser("ingest", help="load filings and deliveries into DuckDB")
    ingest.add_argument(
        "--fixtures",
        type=Path,
        default=None,
        help="directory with companyfacts.json and submissions.json; skips the SEC client",
    )
    ingest.add_argument("--database", type=Path, default=default_database_path())
    ingest.add_argument("--csv", type=Path, default=default_csv_path())
    for name, text in (
        ("model", "write base, bull, and bear forecasts and the backtest"),
        ("variance", "write the revenue, gross profit, operating income, and cash bridges"),
    ):
        stage = subcommands.add_parser(name, help=text)
        stage.add_argument("--database", type=Path, default=default_database_path())
    narrate = subcommands.add_parser("narrate", help="draft and check the memos and Q&A")
    narrate.add_argument("--database", type=Path, default=default_database_path())
    narrate.add_argument(
        "--force", action="store_true", help="call the model even when a verified draft is stored"
    )
    verify = subcommands.add_parser("verify", help="write the verification report per quarter")
    verify.add_argument("--database", type=Path, default=default_database_path())
    publish = subcommands.add_parser("publish", help="write site/public/data/dashboard.json")
    publish.add_argument("--database", type=Path, default=default_database_path())
    publish.add_argument("--output", type=Path, default=DASHBOARD_PATH)
    pipeline = subcommands.add_parser(
        "run", help="run every stage in order and write the dashboard JSON"
    )
    pipeline.add_argument(
        "--database",
        type=Path,
        default=None,
        help="DuckDB file (default data/fpa.duckdb); required with --fixtures",
    )
    pipeline.add_argument(
        "--output",
        type=Path,
        default=None,
        help="dashboard JSON (default site/public/data/dashboard.json); required with --fixtures",
    )
    pipeline.add_argument(
        "--fixtures",
        type=Path,
        default=None,
        help="ingest JSON fixtures from this directory instead of the SEC cache",
    )
    pipeline.add_argument(
        "--force", action="store_true", help="regenerate every narrative, even a cached one"
    )
    args = parser.parse_args(argv)
    try:
        if args.command == "ingest":
            run_ingest(database=args.database, csv_path=args.csv, fixtures=args.fixtures)
            return 0
        if args.command == "run":
            return _run(args.database, args.output, args.fixtures, force=args.force)
        if args.command == "publish":
            return _publish(args.database, args.output)
        if args.command == "narrate":
            return _narrate(args.database, force=args.force)
        if args.command == "verify":
            return _verify(args.database)
        return _run_stage(args.command, args.database)
    except (
        IngestError,
        MissingUserAgentError,
        NarrationError,
        PublishError,
        StageError,
        ValueError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1


def _run(database: Path | None, output: Path | None, fixtures: Path | None, *, force: bool) -> int:
    if fixtures is not None and (database is None or output is None):
        raise StageError(
            "a fixture run needs --database and --output, so fixture numbers never replace "
            "data/fpa.duckdb or the committed dashboard"
        )
    database = default_database_path() if database is None else database
    output = DASHBOARD_PATH if output is None else output
    run = run_pipeline(database=database, output=output, fixtures=fixtures, force=force)
    for stage in run.stages:
        print(f"stage {stage.name}: {_seconds(stage.seconds)} s")
    print(f"run total: {_seconds(run.duration_seconds)} s, model {run.model}")
    print(f"run wrote {output}, data as of {run.data_as_of or 'unknown'}")
    return 0


def _seconds(value: float | None) -> str:
    return "not timed" if value is None else f"{value:.4f}"


def _publish(database: Path, output: Path) -> int:
    if not database.is_file():
        raise StageError(f"{database} does not exist. Run `python -m agent ingest` first.")
    started = datetime.now(UTC)
    connection = duckdb.connect(str(database))
    try:
        apply_schema(connection)
        began = time.perf_counter()
        dashboard = build_dashboard(connection)
        seconds = time.perf_counter() - began
    finally:
        connection.close()
    dashboard = dashboard.model_copy(update={"run": _publish_run(started, seconds)})
    write_dashboard(dashboard, output)
    forward = "on" if dashboard.forward_forecast_published else "off"
    print(
        f"publish wrote {output} with {len(dashboard.quarters)} quarters, "
        f"latest {dashboard.latest_quarter}, forward forecast {forward}"
    )
    return 0


def _publish_run(started: datetime, seconds: float) -> RunMetadata:
    """Only the publish stage is timed here. The other stages are left null."""
    stages = [
        Stage(name=name, seconds=round(seconds, 4) if name == "publish" else None)
        for name in STAGE_NAMES
    ]
    return RunMetadata(
        started_at=started.isoformat(timespec="seconds"),
        duration_seconds=round(seconds, 4),
        stages=stages,
        model=None,
        input_tokens=None,
        output_tokens=None,
        estimated_cost_usd=None,
        data_as_of=None,
    )


def _narrate(database: Path, *, force: bool) -> int:
    _require_database(database)
    client = OpenAIClient()
    connection = _open(database)
    try:
        results = review_all(connection, client, force=force)
    finally:
        connection.close()
    for item in results:
        print(_narrate_line(item))
    reasked = sum(1 for item in results if item.reasked)
    print(f"narrate reviewed {len(results)} quarters, {reasked} re-asked once")
    return 0


def _narrate_line(item: ReviewedNarration) -> str:
    if item.narration.cached:
        state = "cached"
    elif item.reasked:
        state = "re-asked once"
    else:
        state = "drafted"
    counts = item.review.counts
    return (
        f"{item.narration.quarter}: {state}; {counts['verified']} of {counts['total']} "
        f"figures verified, {counts['flagged']} flagged, {counts['unsupported']} unsupported, "
        f"{len(item.review.guard_hits)} keyword guard hit(s)"
    )


def _verify(database: Path) -> int:
    _require_database(database)
    connection = _open(database)
    try:
        reports = verify_all(connection)
    finally:
        connection.close()
    for report in reports:
        print(format_report(report))
        print()
    return 0


def _require_database(database: Path) -> None:
    if not database.is_file():
        raise StageError(f"{database} does not exist. Run `python -m agent ingest` first.")


def _open(database: Path) -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect(str(database))
    apply_schema(connection)
    return connection


def _run_stage(command: str, database: Path) -> int:
    if not database.is_file():
        raise StageError(f"{database} does not exist. Run `python -m agent ingest` first.")
    connection = duckdb.connect(str(database))
    try:
        apply_schema(connection)
        if command == "model":
            forward = Settings().publish_forward_forecast
            result = run_model(connection, publish_forward=forward)
            first, last = result.quarters[0], result.quarters[-1]
            print(f"model wrote forecasts for {len(result.quarters)} quarters, {first} to {last}")
            if result.without_forecast:
                print("no forecast (short history): " + ", ".join(result.without_forecast))
            if result.forward_quarter is None:
                print("forward forecast is off (PUBLISH_FORWARD_FORECAST=false)")
            else:
                print(f"forward forecast written for {result.forward_quarter}")
            return 0
        variance = run_variance(connection)
        print(f"variance wrote {variance.written} bridges")
        for failure in variance.failures:
            print(f"bridge not written: {failure}", file=sys.stderr)
        return 1 if variance.failures else 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
