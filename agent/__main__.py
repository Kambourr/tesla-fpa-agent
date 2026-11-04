"""`python -m agent ingest` loads filings and deliveries.

`--fixtures` reads local JSON. The default path uses the SEC cache. The
command does not print `SEC_USER_AGENT` or `OPENAI_API_KEY`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent.deliveries import default_csv_path
from agent.ingest import IngestError, default_database_path, run_ingest
from agent.sec import MissingUserAgentError


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
    args = parser.parse_args(argv)
    try:
        run_ingest(database=args.database, csv_path=args.csv, fixtures=args.fixtures)
    except (IngestError, MissingUserAgentError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
