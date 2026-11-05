"""The fact sheet names every citable number with a key, period, unit, and source."""

from decimal import Decimal

from agent.fact_sheet import (
    AVERAGE_PERIOD,
    PERCENT,
    UNITS,
    USD,
    USD_PER_UNIT,
    backtest_facts,
    lookup,
    quarter_facts,
    to_json,
)
from agent.model_stage import run_model, run_variance
from pipeline_fixture import build_database

QUARTER = "2026-Q3"


def _sheet():
    connection = build_database()
    run_model(connection, publish_forward=False)
    run_variance(connection)
    return connection, quarter_facts(connection, QUARTER)


def test_actuals_carry_their_filing() -> None:
    connection, facts = _sheet()
    index = lookup(facts)
    revenue = index[("actual.total_revenue", QUARTER)]
    stored = connection.execute(
        "SELECT value, filing_url FROM quarter_actual WHERE quarter = ? AND metric = ?",
        [QUARTER, "total_revenue"],
    ).fetchone()
    assert revenue.value == stored[0]
    assert revenue.unit == USD
    assert revenue.source.startswith("10-Q ")
    assert revenue.source_url == stored[1]
    assert index[("actual.deliveries", QUARTER)].unit == UNITS
    assert index[("actual.automotive_asp", QUARTER)].unit == USD_PER_UNIT
    margin = index[("actual.gross_margin", QUARTER)]
    profit = index[("actual.gross_profit", QUARTER)].value
    assert margin.unit == PERCENT
    assert margin.value == (profit / revenue.value * 100).quantize(Decimal("0.0001"))


def test_forecast_variance_and_bridge_keys() -> None:
    _, facts = _sheet()
    index = lookup(facts)
    actual = index[("actual.total_revenue", QUARTER)].value
    forecast = index[("forecast.base.total_revenue", QUARTER)].value
    assert index[("variance.total_revenue", QUARTER)].value == actual - forecast
    pct = index[("variance_pct.total_revenue", QUARTER)]
    assert pct.unit == PERCENT
    assert pct.value == ((actual - forecast) / forecast * 100).quantize(Decimal("0.0001"))
    assert ("forecast.bull.total_revenue", QUARTER) in index
    assert ("forecast.bear.total_revenue", QUARTER) in index
    margin = index[("forecast.base.gross_margin", QUARTER)]
    assert margin.unit == PERCENT and Decimal(1) < margin.value < Decimal(100)
    bars = [f for f in facts if f.key.startswith("bridge.revenue.")]
    assert len(bars) == 6
    assert sum(f.value for f in bars) == actual - forecast
    assert ("backtest.total_revenue.abs_pct_error", QUARTER) in index


def test_backtest_sheet_has_every_quarter_and_the_average() -> None:
    connection, _ = _sheet()
    facts = backtest_facts(connection)
    quarters = {f.period for f in facts if f.key == "backtest.total_revenue.abs_pct_error"}
    assert len(quarters) == 12
    averages = [f for f in facts if f.period == AVERAGE_PERIOD]
    assert {f.key for f in averages} == {
        "backtest.total_revenue.average_abs_pct_error",
        "backtest.gross_profit.average_abs_pct_error",
        "backtest.operating_income.average_abs_pct_error",
    }


def test_json_keeps_full_precision_and_is_stable() -> None:
    _, facts = _sheet()
    first = to_json(facts)
    assert first == to_json(facts)
    assert '"value": "' in first
