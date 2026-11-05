"""Free cash flow variance in two bars: operating cash flow and capex.

Free cash flow is operating cash flow minus capex, where capex is the positive
purchases of property and equipment. The capex bar is minus the change in
capex, so spending above forecast is unfavorable. Actual free cash flow is not
stored by ingest, so it is computed here from the two first-reported lines.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import duckdb

from agent.bridge import BridgeBar, BridgeError, optional_amount, reconciled, replace_bridge

FREE_CASH_FLOW_BRIDGE = "free_cash_flow"
OPERATING_CASH_FLOW = "net_cash_from_operating_activities"
CAPEX = "purchases_of_property_and_equipment"


@dataclass(frozen=True)
class CashSide:
    """One side of the bridge."""

    operating_cash_flow: Decimal
    capex: Decimal
    free_cash_flow: Decimal


def write_free_cash_flow_bridge(connection: duckdb.DuckDBPyConnection, quarter: str) -> None:
    """Replace the free cash flow bars for one quarter."""
    actual = load_side(connection, quarter, scenario=None)
    forecast = load_side(connection, quarter, scenario="base")
    bars = free_cash_flow_bars(actual, forecast)
    replace_bridge(connection, quarter, FREE_CASH_FLOW_BRIDGE, bars)


def free_cash_flow_bars(actual: CashSide, forecast: CashSide) -> tuple[BridgeBar, ...]:
    """Operating cash flow change, then minus the capex change. They sum exactly."""
    raw = (
        (OPERATING_CASH_FLOW, actual.operating_cash_flow - forecast.operating_cash_flow),
        (CAPEX, -(actual.capex - forecast.capex)),
    )
    return reconciled(raw, actual.free_cash_flow - forecast.free_cash_flow)


def load_side(
    connection: duckdb.DuckDBPyConnection,
    quarter: str,
    *,
    scenario: str | None,
) -> CashSide:
    """Read one side. A missing stored free cash flow is CFO minus capex."""
    cfo = _required(connection, quarter, OPERATING_CASH_FLOW, scenario=scenario)
    capex = _required(connection, quarter, CAPEX, scenario=scenario)
    stored = optional_amount(connection, quarter, "free_cash_flow", scenario=scenario)
    return CashSide(cfo, capex, cfo - capex if stored is None else stored)


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
