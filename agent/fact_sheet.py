"""The numbers the narration may cite, each with a stable key and a source.

This is the contract between narration and verification. Narration gives the
model one quarter's fact sheet (and the backtest sheet for questions 7 and
8). Every claim the model returns must name a fact by ``key`` and ``period``.
The verifier looks the claim up here and compares values. A claim whose key
and period are not on the sheet is ``unsupported``.

Keys:

- ``actual.<metric>``: first-reported value from ``quarter_actual``, plus
  ``actual.deliveries`` (the release), ``actual.automotive_asp``,
  ``actual.gross_margin`` (percent), and ``actual.free_cash_flow``.
- ``forecast.<scenario>.<metric>``: base, bull, and bear forecast lines.
  ``gross_margin`` is converted to percent.
- ``variance.<metric>``: actual minus base forecast, in the metric's unit.
  ``variance_pct.<metric>``: that variance as a percent of the forecast.
  ``variance.gross_margin`` is in percentage points (unit ``percent``).
- ``bridge.<bridge>.<driver>``: one variance bar, in USD.
- ``backtest.<metric>.abs_pct_error``: one quarter's absolute percent error,
  and ``backtest.<metric>.average_abs_pct_error`` with period ``12Q``.

Units are ``USD``, ``percent``, ``units`` (vehicle counts), and
``USD_per_unit`` (ASP).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from decimal import Decimal

import duckdb

from agent.backtest import BACKTEST_METRICS, average_absolute_percent_error

USD = "USD"
PERCENT = "percent"
UNITS = "units"
USD_PER_UNIT = "USD_per_unit"
AVERAGE_PERIOD = "12Q"
_HUNDRED = Decimal(100)
_PLACES = Decimal("0.0001")
_COUNT_METRICS = {"deliveries"}
_ASP_METRICS = {"automotive_asp"}
_RATIO_METRICS = {"gross_margin"}


@dataclass(frozen=True)
class Fact:
    """One citable number."""

    key: str
    period: str
    value: Decimal
    unit: str
    source: str
    source_url: str | None = None

    def as_json(self) -> dict[str, object]:
        """A JSON-ready dict. ``value`` becomes a string so no precision is lost."""
        data = asdict(self)
        data["value"] = str(self.value)
        return data


def quarter_facts(connection: duckdb.DuckDBPyConnection, quarter: str) -> tuple[Fact, ...]:
    """Every citable number for one quarter, actuals first. Deterministic order."""
    facts: list[Fact] = []
    actual = _actuals(connection, quarter)
    facts.extend(actual.values())
    forecasts = _forecasts(connection, quarter)
    facts.extend(forecasts)
    base = {f.key.split(".", 2)[2]: f for f in forecasts if f.key.startswith("forecast.base.")}
    for metric, forecast in base.items():
        found = actual.get(f"actual.{metric}")
        if found is None:
            continue
        change = found.value - forecast.value
        source = "actual minus base forecast"
        facts.append(Fact(f"variance.{metric}", quarter, _q(change), found.unit, source))
        if found.unit != PERCENT and forecast.value != 0:
            facts.append(
                Fact(
                    f"variance_pct.{metric}",
                    quarter,
                    _q(change / abs(forecast.value) * _HUNDRED),
                    PERCENT,
                    "variance as a percent of the base forecast",
                )
            )
    facts.extend(_bridges(connection, quarter))
    facts.extend(f for f in backtest_facts(connection) if f.period == quarter)
    return tuple(facts)


def backtest_facts(connection: duckdb.DuckDBPyConnection) -> tuple[Fact, ...]:
    """Absolute percent error by quarter, then the 12-quarter averages."""
    facts = [
        Fact(f"backtest.{metric}.abs_pct_error", quarter, value, PERCENT, "backtest")
        for quarter, metric, value in connection.execute(
            """
            SELECT quarter, metric, absolute_pct_error FROM backtest
            WHERE absolute_pct_error IS NOT NULL
            ORDER BY quarter, metric
            """
        ).fetchall()
    ]
    for metric, value in average_absolute_percent_error(connection).items():
        if value is not None and metric in BACKTEST_METRICS:
            facts.append(
                Fact(
                    f"backtest.{metric}.average_abs_pct_error",
                    AVERAGE_PERIOD,
                    value,
                    PERCENT,
                    "backtest average across the published quarters",
                )
            )
    return tuple(facts)


def lookup(facts: tuple[Fact, ...]) -> dict[tuple[str, str], Fact]:
    """Index facts by (key, period) for the verifier."""
    return {(fact.key, fact.period): fact for fact in facts}


def to_json(facts: tuple[Fact, ...]) -> str:
    """The sheet as the model sees it: one JSON array, stable order."""
    return json.dumps([fact.as_json() for fact in facts], indent=1)


def _actuals(connection: duckdb.DuckDBPyConnection, quarter: str) -> dict[str, Fact]:
    rows = connection.execute(
        """
        SELECT a.metric, a.value, f.form, a.accession, a.filing_url
        FROM quarter_actual AS a
        LEFT JOIN filing AS f ON f.accession = a.accession
        WHERE a.quarter = ?
        ORDER BY a.metric
        """,
        [quarter],
    ).fetchall()
    facts: dict[str, Fact] = {}
    for metric, value, form, accession, url in rows:
        source = f"{form or 'filing'} {accession}"
        facts[f"actual.{metric}"] = Fact(f"actual.{metric}", quarter, value, USD, source, url)
    delivered = connection.execute(
        "SELECT deliveries_total, source_url FROM deliveries WHERE quarter = ?", [quarter]
    ).fetchone()
    if delivered is not None:
        facts["actual.deliveries"] = Fact(
            "actual.deliveries",
            quarter,
            Decimal(delivered[0]),
            UNITS,
            "production and deliveries release",
            delivered[1],
        )
    sales = facts.get("actual.automotive_sales")
    if sales is not None and delivered is not None and delivered[0]:
        facts["actual.automotive_asp"] = Fact(
            "actual.automotive_asp",
            quarter,
            _q(sales.value / Decimal(delivered[0])),
            USD_PER_UNIT,
            "automotive sales revenue divided by deliveries",
        )
    revenue = facts.get("actual.total_revenue")
    profit = facts.get("actual.gross_profit")
    if revenue is not None and profit is not None and revenue.value:
        facts["actual.gross_margin"] = Fact(
            "actual.gross_margin",
            quarter,
            _q(profit.value / revenue.value * _HUNDRED),
            PERCENT,
            "gross profit divided by total revenue",
        )
    cfo = facts.get("actual.net_cash_from_operating_activities")
    capex = facts.get("actual.purchases_of_property_and_equipment")
    if cfo is not None and capex is not None:
        facts["actual.free_cash_flow"] = Fact(
            "actual.free_cash_flow",
            quarter,
            cfo.value - capex.value,
            USD,
            "operating cash flow minus purchases of property and equipment",
        )
    return facts


def _forecasts(connection: duckdb.DuckDBPyConnection, quarter: str) -> list[Fact]:
    rows = connection.execute(
        """
        SELECT scenario, metric, value, cutoff_date FROM forecast
        WHERE quarter = ? AND value IS NOT NULL
        ORDER BY CASE scenario WHEN 'base' THEN 0 WHEN 'bull' THEN 1 ELSE 2 END, metric
        """,
        [quarter],
    ).fetchall()
    facts: list[Fact] = []
    for scenario, metric, value, cutoff in rows:
        unit = USD
        if metric in _COUNT_METRICS:
            unit = UNITS
        elif metric in _ASP_METRICS:
            unit = USD_PER_UNIT
        elif metric in _RATIO_METRICS:
            unit = PERCENT
            value = _q(value * _HUNDRED)
        facts.append(
            Fact(
                f"forecast.{scenario}.{metric}",
                quarter,
                value,
                unit,
                f"{scenario} forecast, inputs as of {cutoff}",
            )
        )
    return facts


def _bridges(connection: duckdb.DuckDBPyConnection, quarter: str) -> list[Fact]:
    rows = connection.execute(
        """
        SELECT bridge, driver, value FROM bridge
        WHERE quarter = ? ORDER BY bridge, driver
        """,
        [quarter],
    ).fetchall()
    return [
        Fact(f"bridge.{bridge}.{driver}", quarter, value, USD, f"{bridge} bridge")
        for bridge, driver, value in rows
    ]


def _q(value: Decimal) -> Decimal:
    return value.quantize(_PLACES)
