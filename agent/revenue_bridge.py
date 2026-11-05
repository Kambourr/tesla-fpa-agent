"""Revenue waterfall from the base forecast to the first-reported actual.

Six bars: volume, price/mix, regulatory credits, leasing, energy, and
services. Leased units sit inside the delivery total, so the volume bar is
not a pure retail-unit effect. That limitation is for the methods copy.
"""

from __future__ import annotations

from decimal import Decimal

import duckdb

from agent.bridge import BridgeBar, BridgeError, bar, replace_bridge, signed_amount

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
    """Volume, price/mix, and the four revenue deltas. They sum to the variance."""
    actual_deliveries = actual["deliveries"]
    if actual_deliveries == 0:
        raise BridgeError("actual deliveries are zero, so ASP is undefined")
    forecast_asp = forecast["automotive_asp"]
    actual_asp = actual["automotive_sales"] / actual_deliveries
    bars = [
        bar("volume", (actual_deliveries - forecast["deliveries"]) * forecast_asp),
        bar("price_mix", (actual_asp - forecast_asp) * actual_deliveries),
    ]
    for metric in _DELTA_METRICS:
        bars.append(bar(metric, actual[metric] - forecast[metric]))
    return tuple(bars)


def _load(
    connection: duckdb.DuckDBPyConnection,
    quarter: str,
    scenario: str | None,
) -> dict[str, Decimal]:
    # Actual ASP is sales divided by deliveries. Forecast ASP is the stored line.
    if scenario is None:
        metrics = ("deliveries", "automotive_sales", *_DELTA_METRICS)
    else:
        metrics = ("deliveries", "automotive_asp", *_DELTA_METRICS)
    return {
        metric: signed_amount(connection, quarter, metric, scenario=scenario) for metric in metrics
    }
