"""Base forecast from the drivers in ``config/forecast.json``.

Inputs come from ``load_forecast_inputs``, so a filing after the cutoff and
the target quarter's deliveries are already gone. Fewer than
``minimum_earlier_quarters`` of history is an empty forecast: the rows are
stored with a null value and ``empty_history`` set.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import duckdb

from agent.actuals import CASH_FLOW_METRICS
from agent.forecast_config import ForecastConfig, load_forecast_config
from agent.forecast_inputs import (
    ForecastFact,
    ForecastInputs,
    load_forecast_inputs,
    quarter_index,
    shift_quarter,
)

_PLACES = Decimal("0.0001")
_SINGLE_QUARTER = {
    (1, 1, 3, 31): "Q1",
    (4, 1, 6, 30): "Q2",
    (7, 1, 9, 30): "Q3",
    (10, 1, 12, 31): "Q4",
}
_YTD_END = {(3, 31): "Q1", (6, 30): "Q2", (9, 30): "Q3"}

# Lines written for every target quarter. Names match ``quarter_actual`` where
# that table has the series. Capex is ``purchases_of_property_and_equipment``.
BASE_METRICS = (
    "deliveries",
    "automotive_asp",
    "automotive_sales",
    "automotive_regulatory_credits",
    "automotive_leasing",
    "energy_generation_and_storage",
    "services_and_other",
    "total_revenue",
    "gross_margin",
    "gross_profit",
    "operating_expenses",
    "operating_income",
    "net_cash_from_operating_activities",
    "purchases_of_property_and_equipment",
    "free_cash_flow",
)

_RUN_RATE = (
    ("automotive_regulatory_credits", "regulatory_credits"),
    ("automotive_leasing", "leasing"),
    ("energy_generation_and_storage", "energy"),
    ("services_and_other", "services"),
    ("operating_expenses", "operating_expenses"),
)
_OPTIONAL_RUN_RATE = (
    "research_and_development",
    "selling_general_and_administrative",
)


class ForecastError(Exception):
    """The forecast config does not match the driver this module executes."""


@dataclass(frozen=True)
class ForecastLine:
    """One base-forecast amount. ``value`` is null when it cannot be built."""

    metric: str
    value: Decimal | None
    empty_history: bool


def write_base_forecast(connection: duckdb.DuckDBPyConnection, target_quarter: str) -> None:
    """Replace the base scenario for ``target_quarter``. Bull and bear stay."""
    inputs = load_forecast_inputs(connection, target_quarter)
    lines = base_forecast(inputs)
    connection.execute(
        "DELETE FROM forecast WHERE quarter = ? AND scenario = 'base'",
        [target_quarter],
    )
    for line in lines:
        connection.execute(
            "INSERT INTO forecast VALUES (?, ?, 'base', ?, ?, ?)",
            [target_quarter, line.metric, inputs.cutoff_date, line.value, line.empty_history],
        )


def base_forecast(
    inputs: ForecastInputs,
    config: ForecastConfig | None = None,
) -> tuple[ForecastLine, ...]:
    """Forecast one quarter from cutoff inputs. Does not read the database."""
    loaded = load_forecast_config() if config is None else config
    _require_methods(loaded)
    series, deliveries = _series(inputs)
    earlier = _earlier_quarters(series, deliveries, inputs.target_quarter)
    if len(earlier) < loaded.minimum_earlier_quarters:
        return tuple(
            ForecastLine(metric=metric, value=None, empty_history=True) for metric in BASE_METRICS
        )
    return _compute(inputs.target_quarter, series, deliveries)


def _require_methods(config: ForecastConfig) -> None:
    expected = {
        "deliveries": "same_quarter_last_year_times_recent_yoy",
        "automotive_asp": "trailing_four_quarter_average",
        "automotive_sales": "deliveries_times_asp",
        "regulatory_credits": "trailing_run_rate_with_yoy",
        "leasing": "trailing_run_rate_with_yoy",
        "energy": "trailing_run_rate_with_yoy",
        "services": "trailing_run_rate_with_yoy",
        "gross_margin": "trailing_four_quarter_average",
        "operating_expenses": "trailing_run_rate_with_yoy",
        "capex": "trailing_four_quarter_average",
        "operating_cash_flow": "trailing_four_quarter_average",
    }
    for name, method in expected.items():
        if config.drivers[name].method != method:
            found = config.drivers[name].method
            raise ForecastError(f"{name} method is {found}, expected {method}")


def _compute(
    target: str,
    series: dict[str, dict[str, Decimal]],
    deliveries: dict[str, Decimal],
) -> tuple[ForecastLine, ...]:
    amounts: dict[str, Decimal | None] = {}
    amounts["deliveries"] = _deliveries(deliveries, target)
    amounts["automotive_asp"] = _asp(series.get("automotive_sales", {}), deliveries, target)
    sales = amounts["deliveries"]
    asp = amounts["automotive_asp"]
    amounts["automotive_sales"] = None if sales is None or asp is None else sales * asp
    for metric, _driver in _RUN_RATE:
        amounts[metric] = _run_rate(series.get(metric, {}), target)
    for metric in _OPTIONAL_RUN_RATE:
        value = _run_rate(series.get(metric, {}), target)
        if value is not None:
            amounts[metric] = value
    amounts["purchases_of_property_and_equipment"] = _average(
        series.get("purchases_of_property_and_equipment", {}),
        target,
    )
    amounts["net_cash_from_operating_activities"] = _average(
        series.get("net_cash_from_operating_activities", {}),
        target,
    )
    total = _sum(
        amounts.get("automotive_sales"),
        amounts.get("automotive_regulatory_credits"),
        amounts.get("automotive_leasing"),
        amounts.get("energy_generation_and_storage"),
        amounts.get("services_and_other"),
    )
    amounts["total_revenue"] = total
    margin = _margin(series, target, amounts)
    amounts["gross_margin"] = margin
    amounts["gross_profit"] = None if total is None or margin is None else total * margin
    opex = amounts.get("operating_expenses")
    profit = amounts.get("gross_profit")
    amounts["operating_income"] = None if profit is None or opex is None else profit - opex
    cfo = amounts.get("net_cash_from_operating_activities")
    capex = amounts.get("purchases_of_property_and_equipment")
    amounts["free_cash_flow"] = None if cfo is None or capex is None else cfo - capex
    lines = [
        ForecastLine(metric=metric, value=_money(amounts[metric]), empty_history=False)
        for metric in BASE_METRICS
    ]
    for metric in _OPTIONAL_RUN_RATE:
        if metric in amounts:
            lines.append(
                ForecastLine(metric=metric, value=_money(amounts[metric]), empty_history=False)
            )
    return tuple(lines)


def _margin(
    series: dict[str, dict[str, Decimal]],
    target: str,
    amounts: dict[str, Decimal | None],
) -> Decimal | None:
    """Segment margins when all three are in history. Otherwise the total margin.

    The stored gross margin is the margin that turns forecast revenue into
    forecast gross profit, so a later basis-point flex can add to this one number.
    """
    auto = _segment_margin(
        (
            series.get("automotive_sales", {}),
            series.get("automotive_regulatory_credits", {}),
            series.get("automotive_leasing", {}),
        ),
        series.get("cost_of_revenue_automotive", {}),
        target,
    )
    energy = _segment_margin(
        (series.get("energy_generation_and_storage", {}),),
        series.get("cost_of_revenue_energy", {}),
        target,
    )
    services = _segment_margin(
        (series.get("services_and_other", {}),),
        series.get("cost_of_revenue_services", {}),
        target,
    )
    total_revenue = amounts.get("total_revenue")
    segments_ready = auto is not None and energy is not None and services is not None
    if segments_ready and total_revenue not in (None, 0):
        sales = amounts.get("automotive_sales")
        credits = amounts.get("automotive_regulatory_credits")
        leasing = amounts.get("automotive_leasing")
        energy_revenue = amounts.get("energy_generation_and_storage")
        services_revenue = amounts.get("services_and_other")
        parts = (sales, credits, leasing, energy_revenue, services_revenue)
        if any(part is None for part in parts):
            return _total_margin(series, target)
        assert sales is not None and credits is not None and leasing is not None
        assert energy_revenue is not None and services_revenue is not None
        gross = (sales + credits + leasing) * auto
        gross += energy_revenue * energy
        gross += services_revenue * services
        return gross / total_revenue
    return _total_margin(series, target)


def _segment_margin(
    revenues: tuple[dict[str, Decimal], ...],
    cost: dict[str, Decimal],
    target: str,
) -> Decimal | None:
    ratios: list[Decimal] = []
    for offset in (-1, -2, -3, -4):
        quarter = shift_quarter(target, offset)
        parts = [item.get(quarter) for item in revenues]
        spent = cost.get(quarter)
        if any(part is None for part in parts) or spent is None:
            return None
        revenue = sum(parts, Decimal(0))
        if revenue == 0:
            continue
        ratios.append((revenue - spent) / revenue)
    if not ratios:
        return None
    return sum(ratios, Decimal(0)) / Decimal(len(ratios))


def _total_margin(series: dict[str, dict[str, Decimal]], target: str) -> Decimal | None:
    ratios: list[Decimal] = []
    profit = series.get("gross_profit", {})
    revenue = series.get("total_revenue", {})
    for offset in (-1, -2, -3, -4):
        quarter = shift_quarter(target, offset)
        earned = profit.get(quarter)
        sold = revenue.get(quarter)
        if earned is None or sold is None or sold == 0:
            continue
        ratios.append(earned / sold)
    if not ratios:
        return None
    return sum(ratios, Decimal(0)) / Decimal(len(ratios))


def _deliveries(deliveries: dict[str, Decimal], target: str) -> Decimal | None:
    same_quarter = deliveries.get(shift_quarter(target, -4))
    if same_quarter is None:
        return None
    growth = _growth(
        deliveries.get(shift_quarter(target, -1)),
        deliveries.get(shift_quarter(target, -5)),
    )
    return same_quarter * (Decimal(1) + growth)


def _asp(
    sales: dict[str, Decimal],
    deliveries: dict[str, Decimal],
    target: str,
) -> Decimal | None:
    ratios: list[Decimal] = []
    for offset in (-1, -2, -3, -4):
        quarter = shift_quarter(target, offset)
        delivered = deliveries.get(quarter)
        sold = sales.get(quarter)
        if delivered is None or sold is None or delivered == 0:
            continue
        ratios.append(sold / delivered)
    if not ratios:
        return None
    return sum(ratios, Decimal(0)) / Decimal(len(ratios))


def _run_rate(values: dict[str, Decimal], target: str) -> Decimal | None:
    average = _average(values, target)
    if average is None:
        return None
    growth = _growth(values.get(shift_quarter(target, -1)), values.get(shift_quarter(target, -5)))
    return average * (Decimal(1) + growth)


def _average(values: dict[str, Decimal], target: str) -> Decimal | None:
    window: list[Decimal] = []
    for offset in (-1, -2, -3, -4):
        value = values.get(shift_quarter(target, offset))
        if value is None:
            return None
        window.append(value)
    return sum(window, Decimal(0)) / Decimal(len(window))


def _growth(latest: Decimal | None, year_ago: Decimal | None) -> Decimal:
    if latest is None or year_ago is None or year_ago == 0:
        return Decimal(0)
    return latest / year_ago - Decimal(1)


def _sum(*parts: Decimal | None) -> Decimal | None:
    if any(part is None for part in parts):
        return None
    return sum(parts, Decimal(0))


def _money(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value.quantize(_PLACES)


def _series(
    inputs: ForecastInputs,
) -> tuple[dict[str, dict[str, Decimal]], dict[str, Decimal]]:
    grouped: dict[str, list[ForecastFact]] = {}
    for fact in inputs.facts:
        grouped.setdefault(fact.metric, []).append(fact)
    series = {
        metric: _cash_series(facts) if metric in CASH_FLOW_METRICS else _income_series(facts)
        for metric, facts in grouped.items()
    }
    deliveries = {row.quarter: Decimal(row.deliveries_total) for row in inputs.deliveries}
    return series, deliveries


def _income_series(facts: list[ForecastFact]) -> dict[str, Decimal]:
    single: dict[str, Decimal] = {}
    annual: dict[int, Decimal] = {}
    for fact in facts:
        quarter = _single_quarter(fact.period_start, fact.period_end)
        if quarter is not None:
            single[quarter] = fact.value
            continue
        if _is_annual(fact.period_start, fact.period_end):
            annual[fact.period_end.year] = fact.value
    for year, total in annual.items():
        label = f"{year}-Q4"
        if label in single:
            continue
        parts = [single.get(f"{year}-Q{number}") for number in (1, 2, 3)]
        if any(part is None for part in parts):
            continue
        q1, q2, q3 = parts
        assert q1 is not None and q2 is not None and q3 is not None
        single[label] = total - q1 - q2 - q3
    return single


def _cash_series(facts: list[ForecastFact]) -> dict[str, Decimal]:
    ytd: dict[str, Decimal] = {}
    annual: dict[int, Decimal] = {}
    for fact in facts:
        quarter = _ytd_quarter(fact.period_start, fact.period_end)
        if quarter is not None:
            ytd[quarter] = fact.value
        if _is_annual(fact.period_start, fact.period_end):
            annual[fact.period_end.year] = fact.value
    quarters: dict[str, Decimal] = {}
    years = {int(label[:4]) for label in ytd} | set(annual)
    for year in years:
        q1 = ytd.get(f"{year}-Q1")
        q2 = ytd.get(f"{year}-Q2")
        q3 = ytd.get(f"{year}-Q3")
        if q1 is None:
            continue
        quarters[f"{year}-Q1"] = q1
        if q2 is None:
            continue
        single_q2 = q2 - q1
        quarters[f"{year}-Q2"] = single_q2
        if q3 is None:
            continue
        single_q3 = q3 - q2
        quarters[f"{year}-Q3"] = single_q3
        total = annual.get(year)
        if total is not None:
            quarters[f"{year}-Q4"] = total - q1 - single_q2 - single_q3
    return quarters


def _earlier_quarters(
    series: dict[str, dict[str, Decimal]],
    deliveries: dict[str, Decimal],
    target: str,
) -> set[str]:
    target_index = quarter_index(target)
    labels = set(deliveries)
    for values in series.values():
        labels.update(values)
    return {label for label in labels if quarter_index(label) < target_index}


def _single_quarter(start: date, end: date) -> str | None:
    if start.year != end.year:
        return None
    label = _SINGLE_QUARTER.get((start.month, start.day, end.month, end.day))
    if label is None:
        return None
    return f"{end.year}-{label}"


def _ytd_quarter(start: date, end: date) -> str | None:
    if start != date(end.year, 1, 1):
        return None
    label = _YTD_END.get((end.month, end.day))
    if label is None:
        return None
    return f"{end.year}-{label}"


def _is_annual(start: date, end: date) -> bool:
    return start == date(end.year, 1, 1) and end == date(end.year, 12, 31)
