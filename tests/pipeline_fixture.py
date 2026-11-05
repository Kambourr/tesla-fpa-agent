"""A synthetic DuckDB database shaped like a real ingest, for stage tests.

19 quarters, 2022-Q1 through 2026-Q3: Q1 to Q3 come from 10-Qs and Q4 from a
10-K annual amount. Cash-flow lines are year to date, as filed. Every line the
forecast and the bridges read is present, except segment costs, which
companyfacts does not carry. The numbers are invented and are not Tesla's.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import duckdb

from agent.actuals import ReportedFact, assemble_quarter_actuals, store_reported_facts
from agent.schema import apply_schema

FIRST_YEAR = 2022
LATEST = "2026-Q3"
MILLION = 1_000_000
_SEASON = {1: 95, 2: 100, 3: 103, 4: 108}
_ENDS = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
_STARTS = {1: (1, 1), 2: (4, 1), 3: (7, 1), 4: (10, 1)}
_FILED = {1: (4, 25), 2: (7, 25), 3: (10, 25)}
INCOME_METRICS = (
    "automotive_sales",
    "automotive_regulatory_credits",
    "automotive_leasing",
    "energy_generation_and_storage",
    "services_and_other",
    "total_revenue",
    "cost_of_revenue",
    "gross_profit",
    "research_and_development",
    "selling_general_and_administrative",
    "operating_expenses",
    "operating_income",
)
CASH_METRICS = ("net_cash_from_operating_activities", "purchases_of_property_and_equipment")


def quarters() -> list[tuple[int, int]]:
    labels = [(year, number) for year in range(FIRST_YEAR, 2027) for number in (1, 2, 3, 4)]
    return [label for label in labels if f"{label[0]}-Q{label[1]}" <= LATEST]


def deliveries(index: int, number: int) -> int:
    return (300_000 + 8_000 * index) * _SEASON[number] // 100


def amounts(index: int, number: int) -> dict[str, int]:
    """One quarter's single-quarter amounts. Totals tie to their parts."""
    sales = deliveries(index, number) * (45_000 - 150 * index)
    lines = {
        "automotive_sales": sales,
        "automotive_regulatory_credits": (400 + 7 * index) * MILLION,
        "automotive_leasing": (500 - 4 * index) * MILLION,
        "energy_generation_and_storage": (1_500 + 160 * index) * MILLION,
        "services_and_other": (2_000 + 70 * index) * MILLION,
    }
    total = sum(lines.values())
    cost = total * (80 + index % 3) // 100
    research = (900 + 25 * index) * MILLION
    selling = (1_100 + 12 * index) * MILLION
    other = 140 * MILLION if index == 15 else 0
    opex = research + selling + other
    lines.update(
        total_revenue=total,
        cost_of_revenue=cost,
        gross_profit=total - cost,
        research_and_development=research,
        selling_general_and_administrative=selling,
        operating_expenses=opex,
        operating_income=total - cost - opex,
        net_cash_from_operating_activities=(2_500 + 60 * index) * MILLION,
        purchases_of_property_and_equipment=(1_800 + 45 * index) * MILLION,
    )
    return lines


def build_database(path: str = ":memory:") -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect(path)
    apply_schema(connection)
    store_reported_facts(connection, _facts())
    assemble_quarter_actuals(connection)
    for index, (year, number) in enumerate(quarters()):
        release_year, release_month = (year + 1, 1) if number == 4 else (year, number * 3 + 1)
        count = deliveries(index, number)
        connection.execute(
            "INSERT INTO deliveries VALUES (?, ?, ?, ?, ?)",
            [
                f"{year}-Q{number}",
                count + 5_000,
                count,
                date(release_year, release_month, 2),
                f"https://example.com/deliveries/{year}-Q{number}",
            ],
        )
    return connection


def _facts() -> list[ReportedFact]:
    facts: list[ReportedFact] = []
    by_year: dict[int, list[dict[str, int]]] = {}
    for index, (year, number) in enumerate(quarters()):
        values = amounts(index, number)
        by_year.setdefault(year, []).append(values)
        sequence = index + 1
        if number == 4:
            filed = date(year + 1, 1, 28)
            form = "10-K"
            start = date(year, 1, 1)
            income = {metric: sum(q[metric] for q in by_year[year]) for metric in INCOME_METRICS}
        else:
            filed = date(year, *_FILED[number])
            form = "10-Q"
            start = date(year, *_STARTS[number])
            income = {metric: values[metric] for metric in INCOME_METRICS}
        end = date(year, *_ENDS[number])
        accession = f"0000000001-{year % 100:02d}-{sequence:06d}"
        for metric, value in income.items():
            facts.append(_fact(metric, start, end, accession, form, end, filed, value))
        for metric in CASH_METRICS:
            to_date = sum(q[metric] for q in by_year[year])
            facts.append(_fact(metric, date(year, 1, 1), end, accession, form, end, filed, to_date))
    return facts


def _fact(
    metric: str,
    start: date,
    end: date,
    accession: str,
    form: str,
    filing_end: date,
    filed: date,
    value: int,
) -> ReportedFact:
    return ReportedFact(
        metric=metric,
        period_start=start,
        period_end=end,
        accession=accession,
        form=form,
        filing_period_end=filing_end,
        filing_date=filed,
        filing_url=f"https://example.com/{accession}",
        value=Decimal(value),
        unit="USD",
        concept="fixture",
    )
