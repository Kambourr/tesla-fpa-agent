"""The six revenue bars sum to the total revenue variance."""

from datetime import date
from decimal import Decimal

import duckdb

from agent.revenue_bridge import revenue_bars, write_revenue_bridge
from agent.schema import apply_schema

QUARTER = "2024-Q3"


def test_revenue_bars_sum_to_the_variance() -> None:
    forecast = {
        "deliveries": Decimal(100),
        "automotive_asp": Decimal(10),
        "automotive_regulatory_credits": Decimal(20),
        "automotive_leasing": Decimal(30),
        "energy_generation_and_storage": Decimal(40),
        "services_and_other": Decimal(50),
    }
    actual = {
        "deliveries": Decimal(120),
        "automotive_sales": Decimal(1440),
        "automotive_regulatory_credits": Decimal(25),
        "automotive_leasing": Decimal(30),
        "energy_generation_and_storage": Decimal(50),
        "services_and_other": Decimal(40),
    }
    bars = revenue_bars(actual, forecast)
    forecast_total = Decimal(100) * Decimal(10) + Decimal(20 + 30 + 40 + 50)
    actual_total = Decimal(1440) + Decimal(25 + 30 + 50 + 40)
    assert sum((item.value for item in bars), Decimal(0)) == actual_total - forecast_total
    labeled = {item.driver: item for item in bars}
    assert labeled["volume"].value == Decimal("200.0000")
    assert labeled["volume"].favorable is True
    assert labeled["price_mix"].value == Decimal("240.0000")
    assert labeled["automotive_leasing"].value == Decimal("0.0000")
    assert labeled["automotive_leasing"].favorable is False
    assert labeled["services_and_other"].favorable is False
    assert len(bars) == 6


def test_write_revenue_bridge_stores_the_same_bars() -> None:
    connection = duckdb.connect()
    apply_schema(connection)
    forecast = {
        "deliveries": Decimal(100),
        "automotive_asp": Decimal(10),
        "automotive_sales": Decimal(1000),
        "automotive_regulatory_credits": Decimal(20),
        "automotive_leasing": Decimal(30),
        "energy_generation_and_storage": Decimal(40),
        "services_and_other": Decimal(50),
        "total_revenue": Decimal(1140),
    }
    actual = {
        "deliveries": Decimal(120),
        "automotive_sales": Decimal(1440),
        "automotive_regulatory_credits": Decimal(25),
        "automotive_leasing": Decimal(30),
        "energy_generation_and_storage": Decimal(50),
        "services_and_other": Decimal(40),
        "total_revenue": Decimal(1585),
    }
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
    write_revenue_bridge(connection, QUARTER)
    write_revenue_bridge(connection, QUARTER)
    rows = connection.execute(
        """
        SELECT driver, value, favorable
        FROM bridge
        WHERE quarter = ? AND bridge = 'revenue'
        ORDER BY driver
        """,
        [QUARTER],
    ).fetchall()
    assert sum((row[1] for row in rows), Decimal(0)) == Decimal(445)
    assert len(rows) == 6


def test_rounded_forecast_inputs_still_sum_to_the_total_variance() -> None:
    forecast_deliveries = Decimal("100.3333")
    forecast_asp = Decimal("9.8765")
    forecast = {
        "deliveries": forecast_deliveries,
        "automotive_asp": forecast_asp,
        # Stored sales was rounded from unrounded factors, so it is not d * asp.
        "automotive_sales": Decimal("990.9812"),
        "automotive_regulatory_credits": Decimal("20.1111"),
        "automotive_leasing": Decimal("30.2222"),
        "energy_generation_and_storage": Decimal("40.3333"),
        "services_and_other": Decimal("50.4444"),
        "total_revenue": Decimal("1132.0923"),
    }
    actual = {
        "deliveries": Decimal(123),
        "automotive_sales": Decimal(1235),
        "automotive_regulatory_credits": Decimal(25),
        "automotive_leasing": Decimal(31),
        "energy_generation_and_storage": Decimal(47),
        "services_and_other": Decimal(49),
        "total_revenue": Decimal(1387),
    }
    bars = revenue_bars(actual, forecast)
    total = sum((item.value for item in bars), Decimal(0))
    assert total == actual["total_revenue"] - forecast["total_revenue"]
