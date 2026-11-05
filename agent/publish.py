"""Build the one JSON file the static site reads, from the database.

``published_quarter`` decides which quarters appear. A forward quarter is in
that table only when ``PUBLISH_FORWARD_FORECAST`` was true at model time, so
this module never decides on its own to show a forecast. Lines, bridges and
scenarios are read from the stored tables. The only numbers computed here are
the actuals the tables do not store (ASP, gross margin, free cash flow), the
variances and the percent variances, and the favorable flags.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

import duckdb

from agent.backtest import BACKTEST_METRICS, average_absolute_percent_error
from agent.forecast_config import ScenarioFlex as ConfigFlex
from agent.forecast_config import load_forecast_config
from agent.narrative import NarrativeDraft, load_prompts
from agent.publish_schema import (
    Backtest,
    BacktestRow,
    BridgeBar,
    BridgeName,
    ClaimView,
    Dashboard,
    Drivers,
    Filing,
    Memo,
    PnlLine,
    QaAnswer,
    QaSet,
    QuarterView,
    RunMetadata,
    Scenario,
    ScenarioFlex,
    ScenarioTriple,
    Sources,
    Stage,
    StageName,
    Unit,
    VerificationCounts,
)

SCHEMA_VERSION = 1
STAGE_NAMES: tuple[StageName, ...] = ("ingest", "load", "forecast", "explain", "verify", "publish")
SCENARIOS: tuple[Scenario, ...] = ("bull", "base", "bear")
BRIDGE_NAMES: tuple[BridgeName, ...] = (
    "revenue",
    "gross_profit",
    "operating_income",
    "free_cash_flow",
)
_PLACES = Decimal("0.0001")
_PERCENT = Decimal(100)

# Lines in the order the site shows them. A line is written only when it has a
# forecast or an actual for the quarter.
LINE_ORDER: tuple[str, ...] = (
    "deliveries",
    "automotive_asp",
    "automotive_sales",
    "automotive_regulatory_credits",
    "automotive_leasing",
    "energy_generation_and_storage",
    "services_and_other",
    "total_revenue",
    "gross_profit",
    "gross_margin",
    "research_and_development",
    "selling_general_and_administrative",
    "operating_expenses",
    "operating_income",
    "net_cash_from_operating_activities",
    "purchases_of_property_and_equipment",
    "free_cash_flow",
)
# For these, a variance below zero is favorable. For every other line, above zero is.
COST_LINES = frozenset(
    {
        "research_and_development",
        "selling_general_and_administrative",
        "operating_expenses",
        "purchases_of_property_and_equipment",
    }
)
UNITS: dict[str, Unit] = {
    "deliveries": "units",
    "automotive_asp": "USD_per_unit",
    "gross_margin": "percent",
}

# Human labels. Metric lines and bridge drivers share this one dict.
# "energy_generation_and_storage" is both a line and a revenue bridge driver,
# so both read "Energy generation and storage". "energy" is the gross profit
# bridge's segment driver.
LABELS: dict[str, str] = {
    "deliveries": "Deliveries",
    "automotive_asp": "Automotive ASP",
    "automotive_sales": "Automotive sales",
    "automotive_regulatory_credits": "Regulatory credits",
    "automotive_leasing": "Leasing",
    "energy_generation_and_storage": "Energy generation and storage",
    "services_and_other": "Services and other",
    "total_revenue": "Total revenue",
    "gross_profit": "Gross profit",
    "gross_margin": "Gross margin",
    "research_and_development": "R&D",
    "selling_general_and_administrative": "SG&A",
    "operating_expenses": "Operating expenses",
    "operating_income": "Operating income",
    "net_cash_from_operating_activities": "Operating cash flow",
    "purchases_of_property_and_equipment": "Capital expenditures",
    "free_cash_flow": "Free cash flow",
    "volume": "Volume",
    "price_mix": "Price and mix",
    "automotive": "Automotive",
    "energy": "Energy",
    "gross_margin_rate": "Gross margin rate",
    "restructuring_and_other": "Restructuring and other",
}

# Waterfall order of the bars in each bridge. Unknown drivers would sort last.
BRIDGE_ORDER: dict[str, tuple[str, ...]] = {
    "revenue": (
        "volume",
        "price_mix",
        "automotive_regulatory_credits",
        "automotive_leasing",
        "energy_generation_and_storage",
        "services_and_other",
    ),
    "gross_profit": ("automotive", "energy", "services_and_other", "gross_margin_rate"),
    "operating_income": (
        "gross_profit",
        "operating_expenses",
        "research_and_development",
        "selling_general_and_administrative",
        "restructuring_and_other",
    ),
    "free_cash_flow": (
        "net_cash_from_operating_activities",
        "purchases_of_property_and_equipment",
    ),
}

_DRIVER_METRICS = (
    "deliveries",
    "automotive_asp",
    "gross_margin",
    "automotive_regulatory_credits",
    "automotive_leasing",
    "energy_generation_and_storage",
    "services_and_other",
    "operating_expenses",
)


class PublishError(Exception):
    """The database cannot produce a dashboard. The message says what to run first."""


@dataclass(frozen=True)
class _Quarter:
    quarter: str
    kind: Literal["backtest", "forward"]
    has_forecast: bool


def build_dashboard(
    connection: duckdb.DuckDBPyConnection,
    *,
    run: RunMetadata | None = None,
    now: datetime | None = None,
) -> Dashboard:
    """Read the published quarters and their stored tables into one dashboard. Writes nothing."""
    quarters = _published_quarters(connection)
    backtests = [item for item in quarters if item.kind == "backtest"]
    if not backtests:
        raise PublishError(
            "published_quarter is empty. Run `python -m agent model` before `publish`."
        )
    moment = datetime.now(UTC) if now is None else now.astimezone(UTC)
    config = load_forecast_config()
    flex = config.scenarios
    return Dashboard(
        schema_version=1,
        generated_at=moment.isoformat(timespec="seconds"),
        latest_quarter=backtests[-1].quarter,
        forward_forecast_published=any(item.kind == "forward" for item in quarters),
        run=run if run is not None else _empty_run(),
        quarters=[_quarter_view(connection, item) for item in quarters],
        qa=_qa(connection, backtests[-1].quarter),
        backtest=_backtest(connection),
        scenario_flex=ScenarioFlex(
            deliveries_pct=_triple(flex["deliveries"]),
            automotive_asp_pct=_triple(flex["automotive_asp"]),
            gross_margin_bp=_triple(flex["gross_margin"]),
        ),
        sources=_sources(connection),
    )


def write_dashboard(dashboard: Dashboard, path: Path) -> None:
    """Write pretty JSON with sorted keys, indent 2 and a trailing newline."""
    text = json.dumps(dashboard.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _empty_run() -> RunMetadata:
    return RunMetadata(
        started_at=None,
        duration_seconds=None,
        stages=[Stage(name=name, seconds=None) for name in STAGE_NAMES],
        model=None,
        input_tokens=None,
        output_tokens=None,
        estimated_cost_usd=None,
        data_as_of=None,
    )


def _published_quarters(connection: duckdb.DuckDBPyConnection) -> list[_Quarter]:
    rows = connection.execute(
        "SELECT quarter, kind, has_forecast FROM published_quarter ORDER BY quarter"
    ).fetchall()
    return [_Quarter(quarter=row[0], kind=row[1], has_forecast=bool(row[2])) for row in rows]


def _quarter_view(connection: duckdb.DuckDBPyConnection, item: _Quarter) -> QuarterView:
    actual = _actuals(connection, item.quarter)
    base = _forecast(connection, item.quarter, "base")
    return QuarterView(
        quarter=item.quarter,
        label=_label(item.quarter),
        kind=item.kind,
        has_forecast=item.has_forecast,
        filing=_filing(connection, item.quarter),
        lines=_lines(actual, base),
        drivers=_drivers(base) if item.has_forecast else None,
        scenarios=_scenarios(connection, item.quarter),
        bridges={name: _bridge(connection, item.quarter, name) for name in BRIDGE_NAMES},
        memo=_memo(connection, item.quarter),
    )


def _memo(connection: duckdb.DuckDBPyConnection, quarter: str) -> Memo | None:
    """The stored memo and its memo claims. Null when the quarter has no narration."""
    draft = _narrative_draft(connection, quarter)
    if draft is None:
        return None
    claims = [view for location, view in _located_claims(connection, quarter) if location == "memo"]
    return Memo(text=draft.memo.text, claims=claims, verification=_counts(claims))


def _qa(connection: duckdb.DuckDBPyConnection, quarter: str) -> QaSet | None:
    """The stored answers for the latest quarter, each with its claims. Null if none."""
    draft = _narrative_draft(connection, quarter)
    if draft is None or not draft.answers:
        return None
    located = _located_claims(connection, quarter)
    questions = {question.number: question.text for question in load_prompts().questions}
    answers: list[QaAnswer] = []
    claims_all: list[ClaimView] = []
    for answer in sorted(draft.answers, key=lambda item: item.question_number):
        label = f"answer {answer.question_number}"
        claims = [view for location, view in located if location == label]
        claims_all.extend(claims)
        answers.append(
            QaAnswer(
                number=answer.question_number,
                question=questions[answer.question_number],
                text=answer.text,
                claims=claims,
            )
        )
    return QaSet(quarter=quarter, answers=answers, verification=_counts(claims_all))


def _narrative_draft(connection: duckdb.DuckDBPyConnection, quarter: str) -> NarrativeDraft | None:
    row = connection.execute(
        "SELECT payload FROM narrative WHERE quarter = ?", [quarter]
    ).fetchone()
    if row is None:
        return None
    return NarrativeDraft.model_validate_json(str(row[0]))


def _located_claims(
    connection: duckdb.DuckDBPyConnection,
    quarter: str,
) -> list[tuple[str, ClaimView]]:
    """Each stored claim with its location ("memo" or "answer N"). Refuses to guess a status."""
    row = connection.execute(
        "SELECT claims FROM verification WHERE quarter = ?", [quarter]
    ).fetchone()
    if row is None:
        raise PublishError(
            f"{quarter} has a stored narrative but no verification. "
            "Run `python -m agent verify` before `publish`; unverified figures are not published."
        )
    return [(item["location"], _claim_view(item)) for item in json.loads(str(row[0]))]


def _claim_view(item: dict[str, Any]) -> ClaimView:
    expected = item.get("expected")
    return ClaimView(
        metric=item["metric"],
        period=item["period"],
        value=float(item["value"]),
        unit=item["unit"],
        sentence_ref=str(item["sentence_ref"]),
        status=item["status"],
        expected=None if expected is None else float(expected),
        expected_unit=item.get("expected_unit"),
        source=item.get("source"),
        source_url=item.get("source_url"),
    )


def _counts(claims: list[ClaimView]) -> VerificationCounts:
    """Counts over the claims shown beside one block of text, so the ticks and the seal agree."""
    tally = Counter(claim.status for claim in claims)
    return VerificationCounts(
        verified=tally["verified"],
        flagged=tally["flagged"],
        unsupported=tally["unsupported"],
        total=len(claims),
    )


def _label(quarter: str) -> str:
    year, number = quarter.split("-Q")
    return f"Q{number} {year}"


def _actuals(connection: duckdb.DuckDBPyConnection, quarter: str) -> dict[str, Decimal]:
    """First-reported actuals. Deliveries come from their own table, as the bridges read them."""
    values: dict[str, Decimal] = {
        metric: Decimal(value)
        for metric, value in connection.execute(
            "SELECT metric, value FROM quarter_actual WHERE quarter = ?", [quarter]
        ).fetchall()
    }
    found = connection.execute(
        "SELECT deliveries_total FROM deliveries WHERE quarter = ?", [quarter]
    ).fetchone()
    if found is not None and found[0] is not None:
        values["deliveries"] = Decimal(found[0])
    sales = values.get("automotive_sales")
    delivered = values.get("deliveries")
    if sales is not None and delivered:
        values["automotive_asp"] = sales / delivered
    revenue = values.get("total_revenue")
    profit = values.get("gross_profit")
    if revenue is not None and profit is not None and revenue != 0:
        values["gross_margin"] = profit / revenue * _PERCENT
    cash = values.get("net_cash_from_operating_activities")
    capex = values.get("purchases_of_property_and_equipment")
    if cash is not None and capex is not None:
        values["free_cash_flow"] = cash - capex
    return values


def _forecast(
    connection: duckdb.DuckDBPyConnection,
    quarter: str,
    scenario: str,
) -> dict[str, Decimal | None]:
    return {
        metric: value
        for metric, value in connection.execute(
            "SELECT metric, value FROM forecast WHERE quarter = ? AND scenario = ?",
            [quarter, scenario],
        ).fetchall()
    }


def _lines(actual: dict[str, Decimal], base: dict[str, Decimal | None]) -> list[PnlLine]:
    lines: list[PnlLine] = []
    for metric in LINE_ORDER:
        stored = base.get(metric)
        if metric == "gross_margin" and stored is not None:
            # Stored forecast margin is a fraction. The line is in percent.
            stored = stored * _PERCENT
        forecast = _quantized(stored)
        found = _quantized(actual.get(metric))
        if forecast is None and found is None:
            continue
        variance = None if forecast is None or found is None else found - forecast
        variance_pct = None
        if variance is not None and forecast not in (None, Decimal(0)):
            variance_pct = _quantized(variance / abs(forecast) * _PERCENT)
        lines.append(
            PnlLine(
                metric=metric,
                label=LABELS[metric],
                unit=UNITS.get(metric, "USD"),
                forecast=_number(forecast),
                actual=_number(found),
                variance=_number(variance),
                variance_pct=_number(variance_pct),
                favorable=_favorable(metric, variance),
            )
        )
    return lines


def _favorable(metric: str, variance: Decimal | None) -> bool | None:
    if variance is None or variance == 0:
        return None
    if metric in COST_LINES:
        return variance < 0
    return variance > 0


def _drivers(base: dict[str, Decimal | None]) -> Drivers:
    values = {metric: _number(_quantized(base.get(metric))) for metric in _DRIVER_METRICS}
    return Drivers(
        deliveries=values["deliveries"],
        automotive_asp=values["automotive_asp"],
        gross_margin=values["gross_margin"],
        automotive_regulatory_credits=values["automotive_regulatory_credits"],
        automotive_leasing=values["automotive_leasing"],
        energy_generation_and_storage=values["energy_generation_and_storage"],
        services_and_other=values["services_and_other"],
        operating_expenses=values["operating_expenses"],
    )


def _scenarios(
    connection: duckdb.DuckDBPyConnection,
    quarter: str,
) -> dict[Scenario, dict[str, float | None]]:
    """Every scenario has the same metric keys. Gross margin here is a fraction, as stored."""
    rows = connection.execute(
        "SELECT scenario, metric, value FROM forecast WHERE quarter = ?", [quarter]
    ).fetchall()
    metrics = sorted({metric for _, metric, _ in rows})
    stored = {(scenario, metric): value for scenario, metric, value in rows}
    return {
        scenario: {
            metric: _number(_quantized(stored.get((scenario, metric)))) for metric in metrics
        }
        for scenario in SCENARIOS
    }


def _bridge(
    connection: duckdb.DuckDBPyConnection,
    quarter: str,
    name: str,
) -> list[BridgeBar]:
    rows = connection.execute(
        "SELECT driver, value, favorable FROM bridge WHERE quarter = ? AND bridge = ?",
        [quarter, name],
    ).fetchall()
    order = BRIDGE_ORDER[name]
    rows.sort(key=lambda row: (_rank(order, row[0]), row[0]))
    bars: list[BridgeBar] = []
    for driver, value, favorable in rows:
        if driver not in LABELS:
            raise PublishError(f"bridge {name} has driver {driver} with no label")
        bars.append(
            BridgeBar(
                driver=driver,
                label=LABELS[driver],
                value=float(_quantized(value) or Decimal(0)),
                favorable=bool(favorable),
            )
        )
    return bars


def _rank(order: tuple[str, ...], driver: str) -> int:
    return order.index(driver) if driver in order else len(order)


def _filing(connection: duckdb.DuckDBPyConnection, quarter: str) -> Filing | None:
    """The filing that carried total revenue for the quarter. Null for a forward quarter."""
    found = connection.execute(
        """
        SELECT filing.form, filing.accession, filing.filing_date, filing.filing_url
        FROM quarter_actual
        INNER JOIN filing ON filing.accession = quarter_actual.accession
        WHERE quarter_actual.quarter = ? AND quarter_actual.metric = 'total_revenue'
        """,
        [quarter],
    ).fetchone()
    if found is None:
        return None
    form, accession, filed, url = found
    return Filing(form=form, accession=accession, filing_date=filed.isoformat(), url=url)


def _backtest(connection: duckdb.DuckDBPyConnection) -> Backtest:
    rows = connection.execute(
        """
        SELECT backtest.quarter, backtest.metric, backtest.actual,
               backtest.forecast, backtest.absolute_pct_error
        FROM backtest
        INNER JOIN published_quarter ON published_quarter.quarter = backtest.quarter
        WHERE published_quarter.kind = 'backtest'
        ORDER BY backtest.quarter
        """
    ).fetchall()
    ordered = sorted(
        rows,
        key=lambda row: (row[0], _rank(BACKTEST_METRICS, row[1])),
    )
    averages = average_absolute_percent_error(connection)
    return Backtest(
        rows=[
            BacktestRow(
                quarter=quarter,
                metric=metric,
                actual=_number(_quantized(actual)),
                forecast=_number(_quantized(forecast)),
                abs_pct_error=_number(_quantized(error)),
            )
            for quarter, metric, actual, forecast, error in ordered
        ],
        averages={metric: _number(_quantized(averages[metric])) for metric in BACKTEST_METRICS},
    )


def _triple(flex: ConfigFlex) -> ScenarioTriple:
    return ScenarioTriple(bull=float(flex.bull), base=float(flex.base), bear=float(flex.bear))


def _quantized(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value).quantize(_PLACES)


def _number(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _sources(connection: duckdb.DuckDBPyConnection) -> Sources:
    """Counts of what the pipeline loaded, for the page's "what went into it" line."""
    facts, filings = connection.execute(
        "SELECT count(*), count(DISTINCT accession) FROM fact"
    ).fetchone() or (0, 0)
    earliest, latest = connection.execute(
        "SELECT min(filing_date), max(filing_date) FROM filing"
    ).fetchone() or (None, None)
    (deliveries,) = connection.execute("SELECT count(*) FROM deliveries").fetchone() or (0,)
    return Sources(
        facts=int(facts),
        filings=int(filings),
        delivery_quarters=int(deliveries),
        earliest_filing_date=None if earliest is None else str(earliest),
        latest_filing_date=None if latest is None else str(latest),
    )
