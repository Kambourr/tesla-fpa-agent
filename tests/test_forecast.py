"""The base forecast uses cutoff history and is empty without four earlier quarters."""

from datetime import date
from decimal import Decimal

import duckdb

from agent.actuals import ReportedFact, store_reported_facts
from agent.forecast import BASE_METRICS, base_forecast, write_base_forecast
from agent.forecast_inputs import ForecastDelivery, ForecastFact, ForecastInputs
from agent.schema import apply_schema

TARGET = "2024-Q3"


def _bounds(quarter: str) -> tuple[str, str]:
    year = int(quarter[:4])
    number = int(quarter[-1])
    starts = {1: "01-01", 2: "04-01", 3: "07-01", 4: "10-01"}
    ends = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}
    return f"{year}-{starts[number]}", f"{year}-{ends[number]}"


def _income(
    quarter: str,
    metric: str,
    value: int,
    accession: str,
    form: str,
    filed: str,
) -> ReportedFact:
    start, end = _bounds(quarter)
    return ReportedFact(
        metric=metric,
        period_start=date.fromisoformat(start),
        period_end=date.fromisoformat(end),
        accession=accession,
        form=form,
        filing_period_end=date.fromisoformat(end),
        filing_date=date.fromisoformat(filed),
        filing_url=f"https://example.com/{accession}",
        value=Decimal(value),
        unit="USD",
        concept="us-gaap:Revenues",
    )


def _span(
    metric: str,
    start: str,
    end: str,
    value: int,
    accession: str,
    form: str,
    filing_end: str,
    filed: str,
) -> ReportedFact:
    return ReportedFact(
        metric=metric,
        period_start=date.fromisoformat(start),
        period_end=date.fromisoformat(end),
        accession=accession,
        form=form,
        filing_period_end=date.fromisoformat(filing_end),
        filing_date=date.fromisoformat(filed),
        filing_url=f"https://example.com/{accession}",
        value=Decimal(value),
        unit="USD",
        concept="us-gaap:NetCashProvidedByUsedInOperatingActivities",
    )


def _history() -> duckdb.DuckDBPyConnection:
    quarters = {
        "2023-Q2": ("10-Q", "2023-07-20", "0000000001-23-000002", 80),
        "2023-Q3": ("10-Q", "2023-10-20", "0000000001-23-000003", 100),
        "2023-Q4": ("10-K", "2024-01-25", "0000000001-24-000004", 90),
        "2024-Q1": ("10-Q", "2024-04-23", "0000000001-24-000001", 110),
        "2024-Q2": ("10-Q", "2024-07-23", "0000000001-24-000002", 120),
    }
    amounts = {
        "2023-Q2": {
            "automotive_regulatory_credits": 20,
            "automotive_leasing": 4,
            "energy_generation_and_storage": 25,
            "services_and_other": 10,
            "operating_expenses": 50,
        },
        "2023-Q3": {
            "automotive_sales": 800,
            "automotive_regulatory_credits": 10,
            "automotive_leasing": 2,
            "energy_generation_and_storage": 20,
            "services_and_other": 6,
            "total_revenue": 400,
            "gross_profit": 80,
            "operating_expenses": 40,
        },
        "2023-Q4": {
            "automotive_sales": 900,
            "automotive_regulatory_credits": 20,
            "automotive_leasing": 4,
            "energy_generation_and_storage": 30,
            "services_and_other": 9,
            "total_revenue": 600,
            "gross_profit": 120,
            "operating_expenses": 60,
        },
        "2024-Q1": {
            "automotive_sales": 990,
            "automotive_regulatory_credits": 30,
            "automotive_leasing": 6,
            "energy_generation_and_storage": 40,
            "services_and_other": 12,
            "total_revenue": 800,
            "gross_profit": 160,
            "operating_expenses": 80,
        },
        "2024-Q2": {
            "automotive_sales": 1320,
            "automotive_regulatory_credits": 40,
            "automotive_leasing": 8,
            "energy_generation_and_storage": 50,
            "services_and_other": 15,
            "total_revenue": 1000,
            "gross_profit": 200,
            "operating_expenses": 100,
        },
    }
    facts: list[ReportedFact] = []
    for quarter, (form, filed, accession, _delivered) in quarters.items():
        for metric, value in amounts[quarter].items():
            facts.append(_income(quarter, metric, value, accession, form, filed))
    cfo = "net_cash_from_operating_activities"
    capex = "purchases_of_property_and_equipment"
    cash_rows = (
        (cfo, "2023-03-31", 0, "0000000001-23-000003", "10-Q", "2023-09-30", "2023-10-20"),
        (cfo, "2023-06-30", 0, "0000000001-23-000003", "10-Q", "2023-09-30", "2023-10-20"),
        (cfo, "2023-09-30", 20, "0000000001-23-000003", "10-Q", "2023-09-30", "2023-10-20"),
        (cfo, "2023-12-31", 60, "0000000001-24-000004", "10-K", "2023-12-31", "2024-01-25"),
        (cfo, "2024-03-31", 60, "0000000001-24-000001", "10-Q", "2024-03-31", "2024-04-23"),
        (cfo, "2024-06-30", 140, "0000000001-24-000002", "10-Q", "2024-06-30", "2024-07-23"),
        (capex, "2023-03-31", 0, "0000000001-23-000003", "10-Q", "2023-09-30", "2023-10-20"),
        (capex, "2023-06-30", 0, "0000000001-23-000003", "10-Q", "2023-09-30", "2023-10-20"),
        (capex, "2023-09-30", 10, "0000000001-23-000003", "10-Q", "2023-09-30", "2023-10-20"),
        (capex, "2023-12-31", 30, "0000000001-24-000004", "10-K", "2023-12-31", "2024-01-25"),
        (capex, "2024-03-31", 30, "0000000001-24-000001", "10-Q", "2024-03-31", "2024-04-23"),
        (capex, "2024-06-30", 70, "0000000001-24-000002", "10-Q", "2024-06-30", "2024-07-23"),
    )
    for metric, end, value, accession, form, filing_end, filed in cash_rows:
        year = end[:4]
        facts.append(_span(metric, f"{year}-01-01", end, value, accession, form, filing_end, filed))
    facts.append(
        ReportedFact(
            metric="automotive_sales",
            period_start=date(2024, 4, 1),
            period_end=date(2024, 6, 30),
            accession="0000000001-24-000099",
            form="10-Q",
            filing_period_end=date(2024, 9, 30),
            filing_date=date(2024, 10, 23),
            filing_url="https://example.com/restatement",
            value=Decimal(99999),
            unit="USD",
            concept="us-gaap:Revenues",
        )
    )
    connection = duckdb.connect()
    apply_schema(connection)
    store_reported_facts(connection, facts)
    releases = {
        "2023-Q2": ("2023-07-02", 80),
        "2023-Q3": ("2023-10-02", 100),
        "2023-Q4": ("2024-01-02", 90),
        "2024-Q1": ("2024-04-02", 110),
        "2024-Q2": ("2024-07-02", 120),
        "2024-Q3": ("2024-07-02", 999),
    }
    for quarter, (released, delivered) in releases.items():
        connection.execute(
            "INSERT INTO deliveries VALUES (?, ?, ?, ?, ?)",
            [quarter, delivered, delivered, released, f"https://example.com/{quarter}"],
        )
    return connection


def _values(connection: duckdb.DuckDBPyConnection) -> dict[str, Decimal | None]:
    rows = connection.execute(
        """
        SELECT metric, value, empty_history, cutoff_date
        FROM forecast
        WHERE quarter = ? AND scenario = 'base'
        """,
        [TARGET],
    ).fetchall()
    assert rows
    assert {row[3] for row in rows} == {date(2024, 7, 23)}
    assert {row[2] for row in rows} == {False}
    return {row[0]: None if row[1] is None else Decimal(row[1]) for row in rows}


def test_base_forecast_matches_the_driver_formulas() -> None:
    connection = _history()
    write_base_forecast(connection, TARGET)
    write_base_forecast(connection, TARGET)
    stored = _values(connection)
    expected = {
        "deliveries": "150.0000",
        "automotive_asp": "9.5000",
        "automotive_sales": "1425.0000",
        "automotive_regulatory_credits": "50.0000",
        "automotive_leasing": "10.0000",
        "energy_generation_and_storage": "70.0000",
        "services_and_other": "15.7500",
        "total_revenue": "1570.7500",
        "gross_margin": "0.2000",
        "gross_profit": "314.1500",
        "operating_expenses": "140.0000",
        "operating_income": "174.1500",
        "net_cash_from_operating_activities": "50.0000",
        "purchases_of_property_and_equipment": "25.0000",
        "free_cash_flow": "25.0000",
    }
    for metric, value in expected.items():
        assert stored[metric] == Decimal(value), metric
    assert set(BASE_METRICS) <= set(stored)
    count = connection.execute(
        "SELECT count(*) FROM forecast WHERE quarter = ? AND scenario = 'base'",
        [TARGET],
    ).fetchone()
    assert count == (len(BASE_METRICS),)


def test_fewer_than_four_earlier_quarters_is_empty() -> None:
    connection = duckdb.connect()
    apply_schema(connection)
    store_reported_facts(
        connection,
        [
            _income(
                "2024-Q2",
                "total_revenue",
                10,
                "0000000001-24-000002",
                "10-Q",
                "2024-07-23",
            )
        ],
    )
    for quarter, released in (
        ("2024-Q1", "2024-04-02"),
        ("2024-Q2", "2024-07-02"),
        ("2023-Q4", "2024-01-02"),
    ):
        connection.execute(
            "INSERT INTO deliveries VALUES (?, ?, ?, ?, ?)",
            [quarter, 1, 1, released, "https://example.com/short"],
        )
    write_base_forecast(connection, TARGET)
    rows = connection.execute(
        "SELECT metric, value, empty_history FROM forecast WHERE quarter = ? AND scenario = 'base'",
        [TARGET],
    ).fetchall()
    assert len(rows) == len(BASE_METRICS)
    assert {row[1] for row in rows} == {None}
    assert {row[2] for row in rows} == {True}


def test_segment_margins_are_used_when_total_gross_profit_is_absent() -> None:
    quarters = ("2023-Q3", "2023-Q4", "2024-Q1", "2024-Q2")
    facts: list[ForecastFact] = []
    deliveries: list[ForecastDelivery] = []
    for quarter in quarters:
        start, end = _bounds(quarter)
        for metric, value in (
            ("automotive_sales", 100),
            ("automotive_regulatory_credits", 0),
            ("automotive_leasing", 0),
            ("cost_of_revenue_automotive", 50),
            ("energy_generation_and_storage", 50),
            ("cost_of_revenue_energy", 40),
            ("services_and_other", 40),
            ("cost_of_revenue_services", 36),
            ("operating_expenses", 10),
        ):
            facts.append(
                ForecastFact(
                    metric=metric,
                    period_start=date.fromisoformat(start),
                    period_end=date.fromisoformat(end),
                    accession="0000000001-24-000001",
                    filing_date=date(2024, 7, 23),
                    filing_url="https://example.com/q",
                    value=Decimal(value),
                )
            )
        deliveries.append(
            ForecastDelivery(
                quarter=quarter,
                production_total=10,
                deliveries_total=10,
                release_date=date(2024, 7, 2),
            )
        )
    inputs = ForecastInputs(
        target_quarter=TARGET,
        cutoff_date=date(2024, 7, 23),
        cutoff_accession="0000000001-24-000002",
        facts=tuple(facts),
        deliveries=tuple(deliveries),
    )
    lines = {line.metric: line.value for line in base_forecast(inputs)}
    assert lines["gross_profit"] == Decimal("64.0000")
    assert lines["operating_income"] == Decimal("54.0000")
