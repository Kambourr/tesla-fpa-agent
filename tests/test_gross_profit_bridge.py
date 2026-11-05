"""The gross profit bars sum exactly to the gross profit variance."""

from datetime import date
from decimal import Decimal

import duckdb
import pytest

from agent.bridge import BridgeError
from agent.gross_profit_bridge import (
    GrossProfitSide,
    gross_profit_bars,
    write_gross_profit_bridge,
)
from agent.schema import apply_schema

QUARTER = "2024-Q3"

# Forecast: automotive 1000 at 20%, energy 300 at 25%, services 200 at 10%.
FORECAST_LINES = {
    "automotive_sales": Decimal(900),
    "automotive_regulatory_credits": Decimal(50),
    "automotive_leasing": Decimal(50),
    "energy_generation_and_storage": Decimal(300),
    "services_and_other": Decimal(200),
    "total_revenue": Decimal(1500),
    "gross_profit": Decimal(295),
}
FORECAST_SEGMENTS = {
    "gross_profit_automotive": Decimal(200),
    "gross_profit_energy": Decimal(75),
    "gross_profit_services": Decimal(20),
}
# Actual: automotive 1100 at 22%, energy 270 at 20%, services 230 at 10%.
ACTUAL_LINES = {
    "automotive_sales": Decimal(1000),
    "automotive_regulatory_credits": Decimal(40),
    "automotive_leasing": Decimal(60),
    "energy_generation_and_storage": Decimal(270),
    "services_and_other": Decimal(230),
    "total_revenue": Decimal(1600),
    "gross_profit": Decimal(319),
}
ACTUAL_COSTS = {
    "cost_of_revenue_automotive": Decimal(858),
    "cost_of_revenue_energy": Decimal(216),
    "cost_of_revenue_services": Decimal(207),
}


def _side(profit: dict[str, Decimal] | None, *, actual: bool) -> GrossProfitSide:
    lines = ACTUAL_LINES if actual else FORECAST_LINES
    revenue = {
        "automotive": lines["automotive_sales"]
        + lines["automotive_regulatory_credits"]
        + lines["automotive_leasing"],
        "energy": lines["energy_generation_and_storage"],
        "services_and_other": lines["services_and_other"],
    }
    return GrossProfitSide(lines["gross_profit"], lines["total_revenue"], revenue, profit)


ACTUAL_PROFIT = {
    "automotive": Decimal(242),
    "energy": Decimal(54),
    "services_and_other": Decimal(23),
}
FORECAST_PROFIT = {
    "automotive": Decimal(200),
    "energy": Decimal(75),
    "services_and_other": Decimal(20),
}


def test_segment_bars_split_revenue_and_margin_rate() -> None:
    bars = gross_profit_bars(
        _side(ACTUAL_PROFIT, actual=True),
        _side(FORECAST_PROFIT, actual=False),
    )
    labeled = {item.driver: item for item in bars}
    assert set(labeled) == {"automotive", "energy", "services_and_other"}
    # Automotive: 100 more revenue at 20% (+20), margin up 2 points on 1100 (+22).
    assert labeled["automotive"].value == Decimal("42.0000")
    assert labeled["automotive"].favorable is True
    # Energy: 30 less revenue at 25% (-7.5), margin down 5 points on 270 (-13.5).
    assert labeled["energy"].value == Decimal("-21.0000")
    assert labeled["energy"].favorable is False
    # Services: 30 more revenue at 10% (+3), margin flat.
    assert labeled["services_and_other"].value == Decimal("3.0000")
    assert sum((item.value for item in bars), Decimal(0)) == Decimal(319 - 295)


def test_total_margin_path_when_segment_cost_is_missing() -> None:
    bars = gross_profit_bars(_side(None, actual=True), _side(FORECAST_PROFIT, actual=False))
    labeled = {item.driver: item.value for item in bars}
    assert list(labeled) == ["automotive", "energy", "services_and_other", "gross_margin_rate"]
    # Forecast margin is 295/1500. Revenue bars are each segment's change times it.
    assert labeled["automotive"] == Decimal("19.6667")
    assert labeled["energy"] == Decimal("-5.9000")
    assert labeled["services_and_other"] == Decimal("5.9000")
    # (319/1600 - 295/1500) * 1600 = 319 - 314.6667.
    assert labeled["gross_margin_rate"] == Decimal("4.3333")
    assert sum(labeled.values(), Decimal(0)) == Decimal(24)


def test_forecast_without_segments_also_uses_the_total_path() -> None:
    bars = gross_profit_bars(_side(ACTUAL_PROFIT, actual=True), _side(None, actual=False))
    assert bars[-1].driver == "gross_margin_rate"
    assert sum((item.value for item in bars), Decimal(0)) == Decimal(24)


def test_awkward_margins_still_sum_exactly() -> None:
    actual = GrossProfitSide(
        Decimal("4171.3333"),
        Decimal("25182.7777"),
        {
            "automotive": Decimal("19878.1111"),
            "energy": Decimal("3014.3333"),
            "services_and_other": Decimal("2290.3333"),
        },
        None,
    )
    forecast = GrossProfitSide(
        Decimal("4733.9871"),
        Decimal("26001.0003"),
        {
            "automotive": Decimal("20905.0001"),
            "energy": Decimal("2911.0001"),
            "services_and_other": Decimal("2185.0001"),
        },
        None,
    )
    bars = gross_profit_bars(actual, forecast)
    total = sum((item.value for item in bars), Decimal(0))
    assert total == actual.gross_profit - forecast.gross_profit


def test_segment_costs_that_do_not_tie_are_rejected() -> None:
    wrong = dict(ACTUAL_PROFIT, automotive=Decimal(5242))
    with pytest.raises(BridgeError, match="do not tie"):
        gross_profit_bars(_side(wrong, actual=True), _side(FORECAST_PROFIT, actual=False))


def _database(*, with_segments: bool) -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect()
    apply_schema(connection)
    forecast = dict(FORECAST_LINES)
    actual = dict(ACTUAL_LINES)
    if with_segments:
        forecast.update(FORECAST_SEGMENTS)
        actual.update(ACTUAL_COSTS)
    for metric, value in forecast.items():
        connection.execute(
            "INSERT INTO forecast VALUES (?, ?, 'base', ?, ?, false)",
            [QUARTER, metric, date(2024, 7, 23), value],
        )
    for metric, value in actual.items():
        connection.execute(
            "INSERT INTO quarter_actual VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                QUARTER,
                metric,
                value,
                "0000000001-24-000003",
                date(2024, 10, 23),
                "https://example.com/filing",
                "first_reported",
            ],
        )
    return connection


def _stored(connection: duckdb.DuckDBPyConnection) -> dict[str, Decimal]:
    rows = connection.execute(
        "SELECT driver, value FROM bridge WHERE quarter = ? AND bridge = 'gross_profit'",
        [QUARTER],
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def test_write_stores_segment_bars_and_replaces_them() -> None:
    connection = _database(with_segments=True)
    write_gross_profit_bridge(connection, QUARTER)
    write_gross_profit_bridge(connection, QUARTER)
    stored = _stored(connection)
    assert stored == {
        "automotive": Decimal("42.0000"),
        "energy": Decimal("-21.0000"),
        "services_and_other": Decimal("3.0000"),
    }


def test_write_uses_the_total_path_without_segment_lines() -> None:
    connection = _database(with_segments=False)
    write_gross_profit_bridge(connection, QUARTER)
    stored = _stored(connection)
    assert "gross_margin_rate" in stored
    assert sum(stored.values(), Decimal(0)) == Decimal(24)


def test_missing_forecast_gross_profit_is_an_error() -> None:
    connection = _database(with_segments=False)
    connection.execute("DELETE FROM forecast WHERE metric = 'gross_profit'")
    with pytest.raises(BridgeError, match="forecast has no gross_profit"):
        write_gross_profit_bridge(connection, QUARTER)
