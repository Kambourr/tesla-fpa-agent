"""The free cash flow bars sum exactly, and higher capex is unfavorable."""

from datetime import date
from decimal import Decimal

import duckdb
import pytest

from agent.bridge import BridgeError
from agent.free_cash_flow_bridge import (
    CashSide,
    free_cash_flow_bars,
    write_free_cash_flow_bridge,
)
from agent.schema import apply_schema

QUARTER = "2024-Q3"


def test_capex_above_forecast_is_unfavorable() -> None:
    forecast = CashSide(Decimal(3000), Decimal(2000), Decimal(1000))
    actual = CashSide(Decimal(3400), Decimal(2600), Decimal(800))
    bars = free_cash_flow_bars(actual, forecast)
    assert [(item.driver, item.value, item.favorable) for item in bars] == [
        ("net_cash_from_operating_activities", Decimal("400.0000"), True),
        ("purchases_of_property_and_equipment", Decimal("-600.0000"), False),
    ]
    assert sum((item.value for item in bars), Decimal(0)) == Decimal(800 - 1000)


def test_capex_below_forecast_is_favorable() -> None:
    forecast = CashSide(Decimal(3000), Decimal(2000), Decimal(1000))
    actual = CashSide(Decimal(2500), Decimal(1500), Decimal(1000))
    bars = {item.driver: item for item in free_cash_flow_bars(actual, forecast)}
    assert bars["purchases_of_property_and_equipment"].value == Decimal("500.0000")
    assert bars["purchases_of_property_and_equipment"].favorable is True
    assert bars["net_cash_from_operating_activities"].favorable is False


def test_stored_free_cash_flow_that_does_not_tie_is_rejected() -> None:
    forecast = CashSide(Decimal(3000), Decimal(2000), Decimal(1000))
    actual = CashSide(Decimal(3400), Decimal(2600), Decimal(9800))
    with pytest.raises(BridgeError, match="do not tie"):
        free_cash_flow_bars(actual, forecast)


def _database() -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect()
    apply_schema(connection)
    forecast = {
        "net_cash_from_operating_activities": Decimal("3000.1234"),
        "purchases_of_property_and_equipment": Decimal("2000.5678"),
        "free_cash_flow": Decimal("999.5556"),
    }
    for metric, value in forecast.items():
        connection.execute(
            "INSERT INTO forecast VALUES (?, ?, 'base', ?, ?, false)",
            [QUARTER, metric, date(2024, 7, 23), value],
        )
    actual = {
        "net_cash_from_operating_activities": Decimal(3400),
        "purchases_of_property_and_equipment": Decimal(2600),
    }
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


def test_write_computes_actual_free_cash_flow_and_replaces_rows() -> None:
    connection = _database()
    write_free_cash_flow_bridge(connection, QUARTER)
    write_free_cash_flow_bridge(connection, QUARTER)
    rows = connection.execute(
        "SELECT driver, value FROM bridge WHERE quarter = ? AND bridge = 'free_cash_flow'",
        [QUARTER],
    ).fetchall()
    stored = dict(rows)
    assert stored == {
        "net_cash_from_operating_activities": Decimal("399.8766"),
        "purchases_of_property_and_equipment": Decimal("-599.4322"),
    }
    # Actual 3400 - 2600 = 800, forecast 999.5556.
    assert sum(stored.values(), Decimal(0)) == Decimal("-199.5556")


def test_missing_capex_is_an_error() -> None:
    connection = _database()
    connection.execute(
        "DELETE FROM quarter_actual WHERE metric = 'purchases_of_property_and_equipment'"
    )
    with pytest.raises(BridgeError, match="quarter_actual has no purchases_of_property"):
        write_free_cash_flow_bridge(connection, QUARTER)
