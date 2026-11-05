"""The ``model`` and ``variance`` stages.

``run_model`` rebuilds the forecast, scenario, and backtest tables for the
last 12 reported quarters and records them in ``published_quarter``. The next
quarter is forecast and recorded as ``forward`` only when
``PUBLISH_FORWARD_FORECAST`` is true. Otherwise no forward row is written at
all, so nothing downstream can publish one by mistake.

``run_variance`` rebuilds the four bridges for every published backtest
quarter that has a forecast. A bridge that cannot be built is reported, not
skipped quietly, and the command fails.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import duckdb

from agent.backtest import write_backtest
from agent.bridge import BridgeError
from agent.forecast_inputs import shift_quarter
from agent.free_cash_flow_bridge import write_free_cash_flow_bridge
from agent.gross_profit_bridge import write_gross_profit_bridge
from agent.ingest import PUBLISHED_QUARTERS, quarter_window
from agent.operating_income_bridge import write_operating_income_bridge
from agent.revenue_bridge import write_revenue_bridge
from agent.scenarios import write_scenarios

BRIDGES: tuple[tuple[str, Callable[[duckdb.DuckDBPyConnection, str], None]], ...] = (
    ("revenue", write_revenue_bridge),
    ("gross_profit", write_gross_profit_bridge),
    ("operating_income", write_operating_income_bridge),
    ("free_cash_flow", write_free_cash_flow_bridge),
)


class StageError(Exception):
    """A stage could not produce its tables."""


@dataclass(frozen=True)
class ModelResult:
    quarters: tuple[str, ...]
    without_forecast: tuple[str, ...]
    forward_quarter: str | None


@dataclass(frozen=True)
class VarianceResult:
    written: int
    failures: tuple[str, ...]


def published_quarters(connection: duckdb.DuckDBPyConnection) -> tuple[str, ...]:
    """The last 12 quarters with reported total revenue, oldest first."""
    found = connection.execute(
        "SELECT max(quarter) FROM quarter_actual WHERE metric = 'total_revenue'"
    ).fetchone()
    if found is None or found[0] is None:
        raise StageError("quarter_actual has no total_revenue. Run `python -m agent ingest` first.")
    return tuple(quarter_window(found[0], PUBLISHED_QUARTERS))


def run_model(connection: duckdb.DuckDBPyConnection, *, publish_forward: bool) -> ModelResult:
    """Replace forecasts, scenarios, backtest, and the published quarter list."""
    quarters = published_quarters(connection)
    for table in ("forecast", "backtest", "bridge", "published_quarter"):
        connection.execute(f"DELETE FROM {table}")
    without: list[str] = []
    for quarter in quarters:
        write_scenarios(connection, quarter)
        write_backtest(connection, quarter)
        has_forecast = _has_forecast(connection, quarter)
        if not has_forecast:
            without.append(quarter)
        _record(connection, quarter, "backtest", has_forecast)
    forward: str | None = None
    if publish_forward:
        forward = shift_quarter(quarters[-1], 1)
        write_scenarios(connection, forward)
        _record(connection, forward, "forward", _has_forecast(connection, forward))
    return ModelResult(quarters, tuple(without), forward)


def run_variance(connection: duckdb.DuckDBPyConnection) -> VarianceResult:
    """Replace every bridge for the published backtest quarters with a forecast."""
    rows = connection.execute(
        """
        SELECT quarter FROM published_quarter
        WHERE kind = 'backtest' AND has_forecast
        ORDER BY quarter
        """
    ).fetchall()
    if not rows:
        raise StageError("no published quarter has a forecast. Run `python -m agent model` first.")
    connection.execute("DELETE FROM bridge")
    written = 0
    failures: list[str] = []
    for (quarter,) in rows:
        for name, write in BRIDGES:
            try:
                write(connection, quarter)
            except BridgeError as exc:
                failures.append(f"{quarter} {name}: {exc}")
                continue
            written += 1
    return VarianceResult(written, tuple(failures))


def _has_forecast(connection: duckdb.DuckDBPyConnection, quarter: str) -> bool:
    found = connection.execute(
        """
        SELECT count(*) FILTER (WHERE NOT empty_history), count(*)
        FROM forecast
        WHERE quarter = ? AND scenario = 'base'
        """,
        [quarter],
    ).fetchone()
    assert found is not None
    filled, total = found
    return total > 0 and filled == total


def _record(
    connection: duckdb.DuckDBPyConnection,
    quarter: str,
    kind: str,
    has_forecast: bool,
) -> None:
    connection.execute(
        "INSERT INTO published_quarter VALUES (?, ?, ?)",
        [quarter, kind, has_forecast],
    )
