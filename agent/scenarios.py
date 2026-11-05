"""Bull, base, and bear forecasts.

Base is the M2-T3 forecast. Bull and bear flex deliveries, automotive ASP,
and gross margin by the percentages in ``config/forecast.json``. The other
lines stay at base. Sales is flexed deliveries times flexed ASP, so the two
flexes compound.
"""

from __future__ import annotations

from decimal import Decimal

import duckdb

from agent.forecast import BASE_METRICS, SEGMENT_GROSS_PROFIT, ForecastLine, base_forecast
from agent.forecast_config import ForecastConfig, ScenarioFlex, load_forecast_config
from agent.forecast_inputs import ForecastInputs, load_forecast_inputs

_PLACES = Decimal("0.0001")
_SCENARIOS = ("bull", "base", "bear")
_UNFLEXED = (
    "automotive_regulatory_credits",
    "automotive_leasing",
    "energy_generation_and_storage",
    "services_and_other",
    "operating_expenses",
    "net_cash_from_operating_activities",
    "purchases_of_property_and_equipment",
    "free_cash_flow",
    "research_and_development",
    "selling_general_and_administrative",
)


def write_scenarios(connection: duckdb.DuckDBPyConnection, target_quarter: str) -> None:
    """Replace bull, base, and bear for one quarter."""
    inputs = load_forecast_inputs(connection, target_quarter)
    scenarios = scenario_forecasts(inputs)
    connection.execute("DELETE FROM forecast WHERE quarter = ?", [target_quarter])
    cutoff = inputs.cutoff_date
    for name, lines in scenarios.items():
        for line in lines:
            connection.execute(
                "INSERT INTO forecast VALUES (?, ?, ?, ?, ?, ?)",
                [target_quarter, line.metric, name, cutoff, line.value, line.empty_history],
            )


def scenario_forecasts(
    inputs: ForecastInputs,
    config: ForecastConfig | None = None,
) -> dict[str, tuple[ForecastLine, ...]]:
    """Build the three scenarios. Base is ``base_forecast`` unchanged."""
    loaded = load_forecast_config() if config is None else config
    base = base_forecast(inputs, loaded)
    return {
        "base": base,
        "bull": _flex(base, loaded, "bull"),
        "bear": _flex(base, loaded, "bear"),
    }


def _flex(
    base: tuple[ForecastLine, ...],
    config: ForecastConfig,
    scenario: str,
) -> tuple[ForecastLine, ...]:
    values = {line.metric: line.value for line in base}
    empty = any(line.empty_history for line in base)
    if empty:
        return tuple(
            ForecastLine(metric=metric, value=None, empty_history=True) for metric in BASE_METRICS
        )
    deliveries = _apply(values.get("deliveries"), config.scenarios["deliveries"], scenario)
    asp = _apply(values.get("automotive_asp"), config.scenarios["automotive_asp"], scenario)
    margin = _apply(values.get("gross_margin"), config.scenarios["gross_margin"], scenario)
    sales = None if deliveries is None or asp is None else deliveries * asp
    credits = values.get("automotive_regulatory_credits")
    leasing = values.get("automotive_leasing")
    energy = values.get("energy_generation_and_storage")
    services = values.get("services_and_other")
    parts = (sales, credits, leasing, energy, services)
    total = None if any(part is None for part in parts) else sum(parts, Decimal(0))
    profit = None if total is None or margin is None else total * margin
    opex = values.get("operating_expenses")
    income = None if profit is None or opex is None else profit - opex
    flexed = {
        "deliveries": deliveries,
        "automotive_asp": asp,
        "automotive_sales": sales,
        "total_revenue": total,
        "gross_margin": margin,
        "gross_profit": profit,
        "operating_income": income,
    }
    for metric in _UNFLEXED:
        if metric in values:
            flexed[metric] = values[metric]
    ordered = [metric for metric in BASE_METRICS if metric in flexed or metric in values]
    for metric in values:
        # Segment gross profit is base only. The flex moves the blended margin.
        if metric not in ordered and metric not in SEGMENT_GROSS_PROFIT:
            ordered.append(metric)
    return tuple(
        ForecastLine(
            metric=metric,
            value=_money(flexed.get(metric, values.get(metric))),
            empty_history=False,
        )
        for metric in ordered
    )


def _apply(value: Decimal | None, flex: ScenarioFlex, scenario: str) -> Decimal | None:
    if value is None:
        return None
    amount = getattr(flex, scenario)
    if flex.unit == "percent":
        return value * (Decimal(1) + Decimal(amount) / Decimal(100))
    return value + Decimal(amount) / Decimal(10000)


def _money(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value.quantize(_PLACES)
