"""`python -m agent <stage>` runs one pipeline stage.

`ingest` loads filings and deliveries. `--fixtures` reads local JSON, and the
default path uses the SEC cache. `model` writes forecasts, scenarios, and the
backtest. `variance` writes the four bridges. `publish` writes the dashboard
JSON the site reads. No command prints `SEC_USER_AGENT` or `OPENAI_API_KEY`.
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
from agent.publish import STAGE_NAMES, PublishError, build_dashboard, write_dashboard
from agent.publish_schema import RunMetadata, Stage
from agent.schema import apply_schema
from agent.sec import MissingUserAgentError
from agent.settings import Settings

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
    publish = subcommands.add_parser("publish", help="write site/public/data/dashboard.json")
    publish.add_argument("--database", type=Path, default=default_database_path())
    publish.add_argument("--output", type=Path, default=DASHBOARD_PATH)
    args = parser.parse_args(argv)
    try:
        if args.command == "ingest":
            run_ingest(database=args.database, csv_path=args.csv, fixtures=args.fixtures)
            return 0
        if args.command == "publish":
            return _publish(args.database, args.output)
        return _run_stage(args.command, args.database)
    except (IngestError, MissingUserAgentError, PublishError, StageError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


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
