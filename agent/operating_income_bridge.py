"""Operating income waterfall from the base forecast to the first-reported actual.

The first bar is the gross profit variance. Then each operating expense line
is a bar with its sign flipped, so a cost above forecast is unfavorable:
R&D, SG&A, and ``restructuring_and_other``. The last one is total operating
expenses minus R&D and SG&A, which holds restructuring and any other opex
line. When either side lacks R&D or SG&A, one ``operating_expenses`` bar
replaces the three.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import duckdb

from agent.bridge import BridgeBar, BridgeError, optional_amount, reconciled, replace_bridge

OPERATING_INCOME_BRIDGE = "operating_income"
OTHER_OPEX = "restructuring_and_other"
_DETAIL = ("research_and_development", "selling_general_and_administrative")


@dataclass(frozen=True)
class OperatingSide:
    """One side of the bridge. R&D and SG&A are ``None`` when not reported."""

    operating_income: Decimal
    gross_profit: Decimal
    operating_expenses: Decimal
    research_and_development: Decimal | None
    selling_general_and_administrative: Decimal | None


def write_operating_income_bridge(connection: duckdb.DuckDBPyConnection, quarter: str) -> None:
    """Replace the operating income bars for one quarter."""
    actual = load_side(connection, quarter, scenario=None)
    forecast = load_side(connection, quarter, scenario="base")
    bars = operating_income_bars(actual, forecast)
    replace_bridge(connection, quarter, OPERATING_INCOME_BRIDGE, bars)


def operating_income_bars(
    actual: OperatingSide,
    forecast: OperatingSide,
) -> tuple[BridgeBar, ...]:
    """Gross profit, then the cost lines with the sign flipped. They sum exactly."""
    raw: list[tuple[str, Decimal]] = [
        ("gross_profit", actual.gross_profit - forecast.gross_profit),
    ]
    opex_change = actual.operating_expenses - forecast.operating_expenses
    detail = _detail_changes(actual, forecast)
    if detail is None:
        raw.append(("operating_expenses", -opex_change))
    else:
        for metric, change in detail.items():
            raw.append((metric, -change))
        raw.append((OTHER_OPEX, -(opex_change - sum(detail.values(), Decimal(0)))))
    variance = actual.operating_income - forecast.operating_income
    return reconciled(tuple(raw), variance)


def _detail_changes(
    actual: OperatingSide,
    forecast: OperatingSide,
) -> dict[str, Decimal] | None:
    changes: dict[str, Decimal] = {}
    for metric in _DETAIL:
        actual_value = getattr(actual, metric)
        forecast_value = getattr(forecast, metric)
        if actual_value is None or forecast_value is None:
            return None
        changes[metric] = actual_value - forecast_value
    return changes


def load_side(
    connection: duckdb.DuckDBPyConnection,
    quarter: str,
    *,
    scenario: str | None,
) -> OperatingSide:
    """Read one side. Actual gross profit falls back to revenue minus cost."""
    gross_profit = optional_amount(connection, quarter, "gross_profit", scenario=scenario)
    if gross_profit is None and scenario is None:
        revenue = _required(connection, quarter, "total_revenue", scenario=scenario)
        cost = _required(connection, quarter, "cost_of_revenue", scenario=scenario)
        gross_profit = revenue - cost
    if gross_profit is None:
        raise BridgeError(f"forecast has no gross_profit for {quarter}")
    return OperatingSide(
        operating_income=_required(connection, quarter, "operating_income", scenario=scenario),
        gross_profit=gross_profit,
        operating_expenses=_required(connection, quarter, "operating_expenses", scenario=scenario),
        research_and_development=optional_amount(
            connection, quarter, "research_and_development", scenario=scenario
        ),
        selling_general_and_administrative=optional_amount(
            connection, quarter, "selling_general_and_administrative", scenario=scenario
        ),
    )


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
