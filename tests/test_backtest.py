"""Backtest errors stay in the table, including a miss larger than 100 percent."""

from datetime import date
from decimal import Decimal

import duckdb

from agent.backtest import average_absolute_percent_error, write_backtest
from agent.schema import apply_schema


def _store(
    connection: duckdb.DuckDBPyConnection,
    quarter: str,
    metric: str,
    actual: int,
    forecast: int | None,
) -> None:
    connection.execute(
        "INSERT INTO quarter_actual VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            quarter,
            metric,
            Decimal(actual),
            "0000000001-24-000001",
            date(2024, 10, 23),
            "https://example.com/filing",
            "first_reported",
        ],
    )
    connection.execute(
        "INSERT INTO forecast VALUES (?, ?, 'base', ?, ?, false)",
        [quarter, metric, date(2024, 7, 23), None if forecast is None else Decimal(forecast)],
    )


def test_large_errors_are_kept_and_averaged() -> None:
    connection = duckdb.connect()
    apply_schema(connection)
    _store(connection, "2024-Q1", "total_revenue", 100, 80)
    _store(connection, "2024-Q1", "gross_profit", 40, 50)
    _store(connection, "2024-Q1", "operating_income", 10, 30)
    _store(connection, "2024-Q2", "total_revenue", 100, 400)
    _store(connection, "2024-Q2", "gross_profit", 0, 10)
    _store(connection, "2024-Q2", "operating_income", 20, 10)
    write_backtest(connection, "2024-Q1")
    write_backtest(connection, "2024-Q2")
    write_backtest(connection, "2024-Q2")
    stored = {
        (row[0], row[1]): (row[2], row[3])
        for row in connection.execute(
            "SELECT quarter, metric, absolute_pct_error, actual FROM backtest"
        ).fetchall()
    }
    assert stored[("2024-Q1", "total_revenue")][0] == Decimal("20.0000")
    assert stored[("2024-Q1", "gross_profit")][0] == Decimal("25.0000")
    assert stored[("2024-Q1", "operating_income")][0] == Decimal("200.0000")
    assert stored[("2024-Q2", "total_revenue")][0] == Decimal("300.0000")
    assert stored[("2024-Q2", "gross_profit")] == (None, Decimal("0.0000"))
    assert stored[("2024-Q2", "operating_income")][0] == Decimal("50.0000")
    assert len(stored) == 6
    averages = average_absolute_percent_error(connection)
    assert averages["total_revenue"] == Decimal("160.0000")
    assert averages["gross_profit"] == Decimal("25.0000")
    assert averages["operating_income"] == Decimal("125.0000")


def test_a_null_forecast_is_stored_without_an_error() -> None:
    connection = duckdb.connect()
    apply_schema(connection)
    _store(connection, "2024-Q3", "total_revenue", 100, None)
    _store(connection, "2024-Q3", "gross_profit", 40, None)
    _store(connection, "2024-Q3", "operating_income", 10, None)
    write_backtest(connection, "2024-Q3")
    errors = connection.execute("SELECT absolute_pct_error FROM backtest").fetchall()
    assert errors == [(None,), (None,), (None,)]
