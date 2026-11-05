"""Gross profit waterfall from the base forecast to the first-reported actual.

For each segment, the revenue effect is the change in segment revenue times
the forecast segment margin, and the margin-rate effect is the change in
segment margin times actual segment revenue. Each segment's two effects are
one bar: automotive, energy, and services and other.

That needs segment cost on both sides. The forecast has it only when segment
margins were in the cutoff history (``gross_profit_automotive`` and the other
two lines), and the actuals only when the filing's segment cost lines were
loaded. Otherwise the bridge uses the total margin: three revenue bars at the
forecast total margin, plus one ``gross_margin_rate`` bar for the change in
total margin times actual total revenue.

Margins are implied from stored amounts (gross profit divided by revenue)
rather than read from the stored four-place ``gross_margin``, so a rounded
margin cannot move a bar by millions.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import duckdb

from agent.bridge import BridgeBar, BridgeError, optional_amount, reconciled, replace_bridge

GROSS_PROFIT_BRIDGE = "gross_profit"
SEGMENTS = ("automotive", "energy", "services_and_other")
MARGIN_RATE = "gross_margin_rate"

_REVENUE_LINES = {
    "automotive": (
        "automotive_sales",
        "automotive_regulatory_credits",
        "automotive_leasing",
    ),
    "energy": ("energy_generation_and_storage",),
    "services_and_other": ("services_and_other",),
}
_ACTUAL_COST = {
    "automotive": "cost_of_revenue_automotive",
    "energy": "cost_of_revenue_energy",
    "services_and_other": "cost_of_revenue_services",
}
_FORECAST_PROFIT = {
    "automotive": "gross_profit_automotive",
    "energy": "gross_profit_energy",
    "services_and_other": "gross_profit_services",
}


@dataclass(frozen=True)
class GrossProfitSide:
    """One side of the bridge. Segment profit is ``None`` when not reported."""

    gross_profit: Decimal
    total_revenue: Decimal
    segment_revenue: dict[str, Decimal]
    segment_profit: dict[str, Decimal] | None


def write_gross_profit_bridge(connection: duckdb.DuckDBPyConnection, quarter: str) -> None:
    """Replace the gross profit bars for one quarter."""
    actual = load_actual(connection, quarter)
    forecast = load_forecast(connection, quarter)
    replace_bridge(connection, quarter, GROSS_PROFIT_BRIDGE, gross_profit_bars(actual, forecast))


def gross_profit_bars(
    actual: GrossProfitSide,
    forecast: GrossProfitSide,
) -> tuple[BridgeBar, ...]:
    """Segment bars when both sides have segment profit, otherwise the total path."""
    variance = actual.gross_profit - forecast.gross_profit
    if actual.segment_profit is not None and forecast.segment_profit is not None:
        raw = _segment_bars(actual, forecast)
    else:
        raw = _total_bars(actual, forecast)
    return reconciled(raw, variance)


def _segment_bars(
    actual: GrossProfitSide,
    forecast: GrossProfitSide,
) -> tuple[tuple[str, Decimal], ...]:
    assert actual.segment_profit is not None and forecast.segment_profit is not None
    raw: list[tuple[str, Decimal]] = []
    for segment in SEGMENTS:
        forecast_revenue = forecast.segment_revenue[segment]
        actual_revenue = actual.segment_revenue[segment]
        forecast_margin = _ratio(forecast.segment_profit[segment], forecast_revenue)
        actual_margin = _ratio(actual.segment_profit[segment], actual_revenue)
        revenue_effect = (actual_revenue - forecast_revenue) * forecast_margin
        rate_effect = (actual_margin - forecast_margin) * actual_revenue
        raw.append((segment, revenue_effect + rate_effect))
    return tuple(raw)


def _total_bars(
    actual: GrossProfitSide,
    forecast: GrossProfitSide,
) -> tuple[tuple[str, Decimal], ...]:
    if forecast.total_revenue == 0:
        raise BridgeError("forecast total revenue is zero, so the forecast margin is undefined")
    if actual.total_revenue == 0:
        raise BridgeError("actual total revenue is zero, so the actual margin is undefined")
    forecast_margin = forecast.gross_profit / forecast.total_revenue
    actual_margin = actual.gross_profit / actual.total_revenue
    raw = [
        (
            segment,
            (actual.segment_revenue[segment] - forecast.segment_revenue[segment]) * forecast_margin,
        )
        for segment in SEGMENTS
    ]
    raw.append((MARGIN_RATE, (actual_margin - forecast_margin) * actual.total_revenue))
    return tuple(raw)


def _ratio(profit: Decimal, revenue: Decimal) -> Decimal:
    # Zero revenue with zero profit adds nothing at any margin, so use zero.
    if revenue == 0:
        if profit != 0:
            raise BridgeError("a segment has gross profit but no revenue")
        return Decimal(0)
    return profit / revenue


def load_actual(connection: duckdb.DuckDBPyConnection, quarter: str) -> GrossProfitSide:
    """First-reported actuals. Segment profit needs all three segment costs."""
    revenue = _segment_revenue(connection, quarter, scenario=None)
    total = _required(connection, quarter, "total_revenue", scenario=None)
    gross_profit = optional_amount(connection, quarter, "gross_profit", scenario=None)
    if gross_profit is None:
        cost = _required(connection, quarter, "cost_of_revenue", scenario=None)
        gross_profit = total - cost
    costs: dict[str, Decimal] = {}
    for segment, metric in _ACTUAL_COST.items():
        segment_cost = optional_amount(connection, quarter, metric, scenario=None)
        if segment_cost is not None:
            costs[segment] = segment_cost
    profit: dict[str, Decimal] | None = None
    if len(costs) == len(SEGMENTS):
        profit = {segment: revenue[segment] - costs[segment] for segment in SEGMENTS}
    return GrossProfitSide(gross_profit, total, revenue, profit)


def load_forecast(connection: duckdb.DuckDBPyConnection, quarter: str) -> GrossProfitSide:
    """Base forecast. Segment profit exists only when segment margins were used."""
    revenue = _segment_revenue(connection, quarter, scenario="base")
    total = _required(connection, quarter, "total_revenue", scenario="base")
    gross_profit = _required(connection, quarter, "gross_profit", scenario="base")
    found: dict[str, Decimal] = {}
    for segment, metric in _FORECAST_PROFIT.items():
        value = optional_amount(connection, quarter, metric, scenario="base")
        if value is not None:
            found[segment] = value
    profit = found if len(found) == len(SEGMENTS) else None
    return GrossProfitSide(gross_profit, total, revenue, profit)


def _segment_revenue(
    connection: duckdb.DuckDBPyConnection,
    quarter: str,
    scenario: str | None,
) -> dict[str, Decimal]:
    return {
        segment: sum(
            (_required(connection, quarter, metric, scenario=scenario) for metric in metrics),
            Decimal(0),
        )
        for segment, metrics in _REVENUE_LINES.items()
    }


def _required(
    connection: duckdb.DuckDBPyConnection,
    quarter: str,
    metric: str,
    *,
    scenario: str | None,
) -> Decimal:
    value = optional_amount(connection, quarter, metric, scenario=scenario)
    if value is None:
        source = "forecast" if scenario else "quarter_actual"
        raise BridgeError(f"{source} has no {metric} for {quarter}")
    return value
