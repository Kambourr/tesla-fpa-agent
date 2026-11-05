"""The operating income bars sum exactly, and higher costs are unfavorable."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

import duckdb
import pytest

from agent.bridge import BridgeError
from agent.operating_income_bridge import (
    OperatingSide,
    operating_income_bars,
    write_operating_income_bridge,
)
from agent.schema import apply_schema

QUARTER = "2024-Q3"

# Forecast: gross profit 295, opex 200 (R&D 80, SG&A 100, other 20), so 95.
FORECAST = OperatingSide(
    operating_income=Decimal(95),
    gross_profit=Decimal(295),
    operating_expenses=Decimal(200),
    research_and_development=Decimal(80),
    selling_general_and_administrative=Decimal(100),
)
# Actual: gross profit 319, opex 230 (R&D 95, SG&A 105, other 30), so 89.
ACTUAL = OperatingSide(
    operating_income=Decimal(89),
    gross_profit=Decimal(319),
    operating_expenses=Decimal(230),
    research_and_development=Decimal(95),
    selling_general_and_administrative=Decimal(105),
)


def test_higher_costs_are_unfavorable_and_the_bars_sum() -> None:
    bars = operating_income_bars(ACTUAL, FORECAST)
    labeled = {item.driver: item for item in bars}
    assert list(labeled) == [
        "gross_profit",
        "research_and_development",
        "selling_general_and_administrative",
        "restructuring_and_other",
    ]
    assert labeled["gross_profit"].value == Decimal("24.0000")
    assert labeled["gross_profit"].favorable is True
    assert labeled["research_and_development"].value == Decimal("-15.0000")
    assert labeled["research_and_development"].favorable is False
    assert labeled["selling_general_and_administrative"].value == Decimal("-5.0000")
    assert labeled["selling_general_and_administrative"].favorable is False
    assert labeled["restructuring_and_other"].value == Decimal("-10.0000")
    assert sum((item.value for item in bars), Decimal(0)) == Decimal(89 - 95)


def test_lower_costs_are_favorable() -> None:
    cheaper = replace(
        ACTUAL,
        operating_income=Decimal(139),
        operating_expenses=Decimal(180),
        research_and_development=Decimal(70),
        selling_general_and_administrative=Decimal(90),
    )
    labeled = {item.driver: item for item in operating_income_bars(cheaper, FORECAST)}
    assert labeled["research_and_development"].value == Decimal("10.0000")
    assert labeled["research_and_development"].favorable is True
    assert labeled["selling_general_and_administrative"].favorable is True
    assert labeled["restructuring_and_other"].value == Decimal("0.0000")
    assert sum((item.value for item in labeled.values()), Decimal(0)) == Decimal(139 - 95)


def test_one_opex_bar_when_the_detail_is_missing() -> None:
    actual = replace(ACTUAL, research_and_development=None)
    bars = operating_income_bars(actual, FORECAST)
    assert [(item.driver, item.value) for item in bars] == [
        ("gross_profit", Decimal("24.0000")),
        ("operating_expenses", Decimal("-30.0000")),
    ]
    assert bars[1].favorable is False


def test_operating_income_that_does_not_tie_is_rejected() -> None:
    wrong = replace(ACTUAL, operating_income=Decimal(5089))
    with pytest.raises(BridgeError, match="do not tie"):
        operating_income_bars(wrong, FORECAST)


def _database() -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect()
    apply_schema(connection)
    for metric in (
        "operating_income",
        "gross_profit",
        "operating_expenses",
        "research_and_development",
        "selling_general_and_administrative",
    ):
        connection.execute(
            "INSERT INTO forecast VALUES (?, ?, 'base', ?, ?, false)",
            [QUARTER, metric, date(2024, 7, 23), getattr(FORECAST, metric)],
        )
    actual = {
        "operating_income": ACTUAL.operating_income,
        "total_revenue": Decimal(1600),
        "cost_of_revenue": Decimal(1281),
        "operating_expenses": ACTUAL.operating_expenses,
        "research_and_development": ACTUAL.research_and_development,
        "selling_general_and_administrative": ACTUAL.selling_general_and_administrative,
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


def test_write_stores_the_bars_with_gross_profit_from_revenue_less_cost() -> None:
    connection = _database()
    write_operating_income_bridge(connection, QUARTER)
    write_operating_income_bridge(connection, QUARTER)
    rows = connection.execute(
        """
        SELECT driver, value, favorable FROM bridge
        WHERE quarter = ? AND bridge = 'operating_income'
        """,
        [QUARTER],
    ).fetchall()
    stored = {row[0]: (row[1], row[2]) for row in rows}
    assert stored["gross_profit"] == (Decimal("24.0000"), True)
    assert stored["research_and_development"] == (Decimal("-15.0000"), False)
    assert sum((value for value, _ in stored.values()), Decimal(0)) == Decimal(-6)


def test_missing_operating_income_is_an_error() -> None:
    connection = _database()
    connection.execute("DELETE FROM quarter_actual WHERE metric = 'operating_income'")
    with pytest.raises(BridgeError, match="quarter_actual has no operating_income"):
        write_operating_income_bridge(connection, QUARTER)
