"""Absolute percent error of the base forecast against first-reported actuals.

The error is a percent: 100 means the forecast missed the actual by the whole
actual. A miss larger than 100 percent is stored as that larger number. An
actual of zero is stored with a null error, because the ratio is undefined.
The average is the mean of the stored errors and is not a fake quarter.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import duckdb

_PLACES = Decimal("0.0001")
BACKTEST_METRICS = ("total_revenue", "gross_profit", "operating_income")


@dataclass(frozen=True)
class BacktestRow:
    """One forecast-versus-actual comparison. ``absolute_pct_error`` may be null."""

    quarter: str
    metric: str
    actual: Decimal | None
    forecast: Decimal | None
    absolute_pct_error: Decimal | None


def write_backtest(connection: duckdb.DuckDBPyConnection, quarter: str) -> None:
    """Replace the three accuracy rows for one quarter. Does not drop a large error."""
    rows = backtest_rows(connection, quarter)
    connection.execute("DELETE FROM backtest WHERE quarter = ?", [quarter])
    for row in rows:
        connection.execute(
            "INSERT INTO backtest VALUES (?, ?, ?, ?, ?)",
            [row.quarter, row.metric, row.actual, row.forecast, row.absolute_pct_error],
        )


def backtest_rows(connection: duckdb.DuckDBPyConnection, quarter: str) -> tuple[BacktestRow, ...]:
    """Read base-forecast and quarter-actual amounts for the three lines."""
    rows: list[BacktestRow] = []
    for metric in BACKTEST_METRICS:
        forecast = _amount(
            connection,
            "SELECT value FROM forecast WHERE quarter = ? AND metric = ? AND scenario = 'base'",
            [quarter, metric],
        )
        if forecast is _MISSING:
            continue
        actual = _amount(
            connection,
            "SELECT value FROM quarter_actual WHERE quarter = ? AND metric = ?",
            [quarter, metric],
        )
        actual_value = None if actual is _MISSING else actual
        forecast_value = forecast if isinstance(forecast, Decimal) or forecast is None else None
        rows.append(
            BacktestRow(
                quarter=quarter,
                metric=metric,
                actual=actual_value,
                forecast=forecast_value,
                absolute_pct_error=_error(actual_value, forecast_value),
            )
        )
    return tuple(rows)


def average_absolute_percent_error(
    connection: duckdb.DuckDBPyConnection,
) -> dict[str, Decimal | None]:
    """Mean of stored errors by metric. Null errors stay out of the mean and in the table."""
    averages: dict[str, Decimal | None] = {}
    for metric in BACKTEST_METRICS:
        values = connection.execute(
            """
            SELECT absolute_pct_error
            FROM backtest
            WHERE metric = ? AND absolute_pct_error IS NOT NULL
            """,
            [metric],
        ).fetchall()
        if not values:
            averages[metric] = None
            continue
        total = sum((row[0] for row in values), Decimal(0))
        averages[metric] = (total / Decimal(len(values))).quantize(_PLACES)
    return averages


class _Missing:
    pass


_MISSING = _Missing()


def _amount(
    connection: duckdb.DuckDBPyConnection,
    query: str,
    parameters: list[str],
) -> Decimal | None | _Missing:
    found = connection.execute(query, parameters).fetchone()
    if found is None:
        return _MISSING
    return found[0]


def _error(actual: Decimal | None, forecast: Decimal | None) -> Decimal | None:
    if actual is None or forecast is None or actual == 0:
        return None
    return (abs(forecast - actual) / abs(actual) * Decimal(100)).quantize(_PLACES)
