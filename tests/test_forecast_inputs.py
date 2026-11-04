"""The forecast for Q reads only what existed on the previous quarter's filing date."""

from datetime import date
from decimal import Decimal

import duckdb
import pytest

from agent.actuals import ReportedFact, assemble_quarter_actuals, store_reported_facts
from agent.forecast_inputs import CutoffError, load_forecast_inputs
from agent.schema import apply_schema

Q1_URL = "https://www.sec.gov/Archives/edgar/data/1318605/000000000124000001/q1.htm"
Q1A_URL = "https://www.sec.gov/Archives/edgar/data/1318605/000000000124000003/q1a.htm"
Q2_URL = "https://www.sec.gov/Archives/edgar/data/1318605/000000000124000002/q2.htm"


def _fact(
    *,
    accession: str,
    form: str,
    filing_end: str,
    filed: str,
    url: str,
    value: int,
    start: str = "2024-01-01",
    end: str = "2024-03-31",
) -> ReportedFact:
    return ReportedFact(
        metric="total_revenue",
        period_start=date.fromisoformat(start),
        period_end=date.fromisoformat(end),
        accession=accession,
        form=form,
        filing_period_end=date.fromisoformat(filing_end),
        filing_date=date.fromisoformat(filed),
        filing_url=url,
        value=Decimal(value),
        unit="USD",
        concept="us-gaap:Revenues",
    )


def _database() -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect()
    apply_schema(connection)
    store_reported_facts(
        connection,
        [
            _fact(
                accession="0000000001-24-000001",
                form="10-Q",
                filing_end="2024-03-31",
                filed="2024-04-23",
                url=Q1_URL,
                value=100,
            ),
            _fact(
                accession="0000000001-24-000003",
                form="10-Q/A",
                filing_end="2024-03-31",
                filed="2024-05-01",
                url=Q1A_URL,
                value=105,
            ),
            _fact(
                accession="0000000001-24-000002",
                form="10-Q",
                filing_end="2024-06-30",
                filed="2024-07-23",
                url=Q2_URL,
                value=110,
            ),
        ],
    )
    assemble_quarter_actuals(connection)
    connection.execute(
        "INSERT INTO deliveries VALUES (?, ?, ?, ?, ?)",
        ["2024-Q1", 10, 9, date(2024, 4, 2), "https://example.com/q1"],
    )
    connection.execute(
        "INSERT INTO deliveries VALUES (?, ?, ?, ?, ?)",
        ["2024-Q2", 80, 70, date(2024, 4, 20), "https://example.com/q2"],
    )
    connection.execute(
        "INSERT INTO deliveries VALUES (?, ?, ?, ?, ?)",
        ["2024-Q3", 30, 25, date(2024, 7, 2), "https://example.com/q3"],
    )
    return connection


def test_cutoff_is_the_previous_quarters_first_filing() -> None:
    connection = _database()
    inputs = load_forecast_inputs(connection, "2024-Q2")
    assert inputs.cutoff_date == date(2024, 4, 23)
    assert inputs.cutoff_accession == "0000000001-24-000001"
    assert inputs.target_quarter == "2024-Q2"


def test_q2_forecast_skips_later_filings_and_its_own_deliveries() -> None:
    connection = _database()
    inputs = load_forecast_inputs(connection, "2024-Q2")
    assert [fact.filing_date for fact in inputs.facts] == [date(2024, 4, 23)]
    assert int(inputs.facts[0].value) == 100
    assert inputs.facts[0].accession == "0000000001-24-000001"
    assert [row.quarter for row in inputs.deliveries] == ["2024-Q1"]
    assert inputs.deliveries[0].deliveries_total == 9
    assert inputs.deliveries[0].production_total == 10
    assert 70 not in [row.deliveries_total for row in inputs.deliveries]
    assert 80 not in [row.production_total for row in inputs.deliveries]


def test_later_cutoff_uses_the_restatement_not_the_first_report() -> None:
    connection = _database()
    inputs = load_forecast_inputs(connection, "2024-Q3")
    assert inputs.cutoff_date == date(2024, 7, 23)
    q1 = [fact for fact in inputs.facts if fact.period_end == date(2024, 3, 31)]
    assert len(q1) == 1
    assert int(q1[0].value) == 110
    assert q1[0].filing_date == date(2024, 7, 23)
    first_reported = connection.execute(
        """
        SELECT value FROM quarter_actual
        WHERE quarter = '2024-Q1' AND metric = 'total_revenue'
        """
    ).fetchone()
    assert first_reported is not None
    assert int(first_reported[0]) == 100
    assert [row.quarter for row in inputs.deliveries] == ["2024-Q1", "2024-Q2"]
    assert 25 not in [row.deliveries_total for row in inputs.deliveries]


def test_missing_previous_filing_has_no_cutoff() -> None:
    connection = duckdb.connect()
    apply_schema(connection)
    with pytest.raises(CutoffError, match="2024-Q1"):
        load_forecast_inputs(connection, "2024-Q2")
