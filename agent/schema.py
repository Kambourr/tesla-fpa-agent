"""Apply the SQL files that define the local database.

The table shapes and the as-of query live in `sql/`. This module only runs
those files, in name order, against a DuckDB connection.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

SQL_DIR = Path(__file__).resolve().parents[1] / "sql"


def apply_schema(
    connection: duckdb.DuckDBPyConnection,
    sql_dir: Path | None = None,
) -> None:
    """Run every `sql/*.sql` file. Does not fetch filings or read the CSV."""
    directory = SQL_DIR if sql_dir is None else sql_dir
    paths = sorted(directory.glob("*.sql"))
    if not paths:
        raise FileNotFoundError(f"no SQL files in {directory}")
    for path in paths:
        connection.execute(path.read_text(encoding="utf-8"))
