"""Applying sql/ creates the raw tables, the later tables, and the as-of query."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import duckdb

from agent.schema import SQL_DIR, apply_schema

REPO_ROOT = Path(__file__).resolve().parents[1]

RAW_TABLES = {"filing", "fact", "deliveries"}
LATER_TABLES = {"quarter_actual", "forecast", "bridge", "backtest"}


def test_applying_sql_creates_raw_and_later_tables() -> None:
    connection = duckdb.connect()
    apply_schema(connection)
    rows = connection.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'main' AND table_type = 'BASE TABLE'
        """
    ).fetchall()
    names = {row[0] for row in rows}
    assert names >= RAW_TABLES
    assert names >= LATER_TABLES
    view = connection.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'main' AND table_name = 'fact_with_source'
        """
    ).fetchall()
    assert view == [("fact_with_source",)]
    macro = connection.execute(
        """
        SELECT function_name
        FROM duckdb_functions()
        WHERE function_name = 'fact_as_of'
        """
    ).fetchall()
    assert macro == [("fact_as_of",)]


def test_deliveries_columns_match_the_csv() -> None:
    connection = duckdb.connect()
    apply_schema(connection)
    rows = connection.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'deliveries'
        ORDER BY ordinal_position
        """
    ).fetchall()
    assert [row[0] for row in rows] == [
        "quarter",
        "production_total",
        "deliveries_total",
        "release_date",
        "source_url",
    ]


def test_fact_as_of_keeps_the_older_filing() -> None:
    connection = duckdb.connect()
    apply_schema(connection)
    connection.execute(
        """
        INSERT INTO filing VALUES
            ('AAA', '10-Q', DATE '2024-03-31', DATE '2024-04-23', 'https://example.test/a'),
            ('BBB', '10-Q', DATE '2024-06-30', DATE '2024-07-23', 'https://example.test/b')
        """
    )
    connection.execute(
        """
        INSERT INTO fact VALUES
            (
                'total_revenue', DATE '2024-01-01', DATE '2024-03-31', 'AAA',
                100, 'USD', 'us-gaap:Revenues', NULL
            ),
            (
                'total_revenue', DATE '2024-01-01', DATE '2024-03-31', 'BBB',
                110, 'USD', 'us-gaap:Revenues', NULL
            )
        """
    )
    early = connection.execute(
        "SELECT accession, value FROM fact_as_of(DATE '2024-05-01')"
    ).fetchall()
    later = connection.execute(
        "SELECT accession, value FROM fact_as_of(DATE '2024-08-01')"
    ).fetchall()
    stored = connection.execute("SELECT count(*) FROM fact").fetchone()
    assert early == [("AAA", Decimal("100.0000"))]
    assert later == [("BBB", Decimal("110.0000"))]
    assert stored == (2,)
    source = connection.execute(
        """
        SELECT filing_date, filing_url
        FROM fact_with_source
        WHERE accession = 'AAA'
        """
    ).fetchone()
    assert source == (date(2024, 4, 23), "https://example.test/a")


def test_schema_can_be_applied_twice() -> None:
    connection = duckdb.connect()
    apply_schema(connection)
    apply_schema(connection)
    count = connection.execute(
        """
        SELECT count(*)
        FROM information_schema.tables
        WHERE table_schema = 'main' AND table_name = 'fact'
        """
    ).fetchone()
    assert count == (1,)


def test_transforms_live_in_sql_files() -> None:
    source = (REPO_ROOT / "agent" / "schema.py").read_text(encoding="utf-8")
    assert "CREATE TABLE" not in source
    assert "CREATE OR REPLACE" not in source
    sql_files = sorted(path.name for path in SQL_DIR.glob("*.sql"))
    assert "009_fact_as_of.sql" in sql_files
    as_of = (SQL_DIR / "009_fact_as_of.sql").read_text(encoding="utf-8")
    assert "CREATE OR REPLACE MACRO fact_as_of" in as_of
    assert "PARTITION BY metric, period_start, period_end" in as_of
