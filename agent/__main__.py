"""`python -m agent <stage>` runs one pipeline stage.

`ingest` loads filings and deliveries. `--fixtures` reads local JSON, and the
default path uses the SEC cache. `model` writes forecasts, scenarios, and the
backtest. `variance` writes the four bridges. No command prints
`SEC_USER_AGENT` or `OPENAI_API_KEY`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb

from agent.deliveries import default_csv_path
from agent.ingest import IngestError, default_database_path, run_ingest
from agent.model_stage import StageError, run_model, run_variance
from agent.schema import apply_schema
from agent.sec import MissingUserAgentError
from agent.settings import Settings


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
    args = parser.parse_args(argv)
    try:
        if args.command == "ingest":
            run_ingest(database=args.database, csv_path=args.csv, fixtures=args.fixtures)
            return 0
        return _run_stage(args.command, args.database)
    except (IngestError, MissingUserAgentError, StageError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


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
