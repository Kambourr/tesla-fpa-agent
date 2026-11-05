"""Revenue waterfall from the base forecast to the first-reported actual.

Six bars: volume, price/mix, regulatory credits, leasing, energy, and
services. Leased units sit inside the delivery total, so the volume bar is
not a pure retail-unit effect. That limitation is for the methods copy.
"""

from __future__ import annotations

from decimal import Decimal

import duckdb

from agent.bridge import (
    BridgeBar,
    BridgeError,
    optional_amount,
    reconciled,
    replace_bridge,
    signed_amount,
)

REVENUE_BRIDGE = "revenue"
_DELTA_METRICS = (
    "automotive_regulatory_credits",
    "automotive_leasing",
    "energy_generation_and_storage",
    "services_and_other",
)


def write_revenue_bridge(connection: duckdb.DuckDBPyConnection, quarter: str) -> None:
    """Replace the revenue bars for one quarter."""
    actual = _load(connection, quarter, scenario=None)
    forecast = _load(connection, quarter, scenario="base")
    replace_bridge(connection, quarter, REVENUE_BRIDGE, revenue_bars(actual, forecast))


def revenue_bars(
    actual: dict[str, Decimal],
    forecast: dict[str, Decimal],
) -> tuple[BridgeBar, ...]:
    """Volume, price/mix, and the four revenue deltas. They sum to the variance.

    The variance is actual total revenue minus forecast total revenue, or the
    sum of the revenue lines when a total is not given. Stored
    forecast sales is rounded, so it can differ by cents from forecast
    deliveries times forecast ASP. ``reconciled`` absorbs that gap.
    """
    actual_deliveries = actual["deliveries"]
    if actual_deliveries == 0:
        raise BridgeError("actual deliveries are zero, so ASP is undefined")
    forecast_asp = forecast["automotive_asp"]
    forecast_sales = forecast.get("automotive_sales")
    if forecast_sales is None:
        forecast_sales = forecast["deliveries"] * forecast_asp
    actual_asp = actual["automotive_sales"] / actual_deliveries
    raw = [
        ("volume", (actual_deliveries - forecast["deliveries"]) * forecast_asp),
        ("price_mix", (actual_asp - forecast_asp) * actual_deliveries),
    ]
    variance = actual["automotive_sales"] - forecast_sales
    for metric in _DELTA_METRICS:
        delta = actual[metric] - forecast[metric]
        raw.append((metric, delta))
        variance += delta
    if "total_revenue" in actual and "total_revenue" in forecast:
        # Tie to the stored totals. A gap above the rounding limit means the
        # revenue lines do not add up to total revenue on one side.
        variance = actual["total_revenue"] - forecast["total_revenue"]
    return reconciled(tuple(raw), variance)


def _load(
    connection: duckdb.DuckDBPyConnection,
    quarter: str,
    scenario: str | None,
) -> dict[str, Decimal]:
    # Actual ASP is sales divided by deliveries. Forecast ASP is the stored line.
    if scenario is None:
        metrics = ("automotive_sales", *_DELTA_METRICS)
    else:
        metrics = ("deliveries", "automotive_asp", *_DELTA_METRICS)
    loaded = {
        metric: signed_amount(connection, quarter, metric, scenario=scenario) for metric in metrics
    }
    if scenario is None:
        # Ingest keeps delivery counts in the deliveries table, not quarter_actual.
        loaded["deliveries"] = _actual_deliveries(connection, quarter)
    extras = ("automotive_sales", "total_revenue") if scenario else ("total_revenue",)
    for metric in extras:
        value = optional_amount(connection, quarter, metric, scenario=scenario)
        if value is not None:
            loaded[metric] = value
    return loaded


def _actual_deliveries(connection: duckdb.DuckDBPyConnection, quarter: str) -> Decimal:
    found = connection.execute(
        "SELECT deliveries_total FROM deliveries WHERE quarter = ?",
        [quarter],
    ).fetchone()
    if found is None or found[0] is None:
        raise BridgeError(f"deliveries has no total for {quarter}")
    return Decimal(found[0])
