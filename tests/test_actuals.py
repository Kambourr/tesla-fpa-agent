"""Per-filing facts stay stored, and quarter actuals keep the first report."""

from datetime import date
from decimal import Decimal

import duckdb

from agent.actuals import (
    ReportedFact,
    assemble_quarter_actuals,
    facts_from_companyfacts,
    store_reported_facts,
)
from agent.schema import apply_schema
from agent.xbrl_map import load_xbrl_map

Q1_URL = "https://www.sec.gov/Archives/edgar/data/1318605/000000000124000001/q1.htm"
Q2_URL = "https://www.sec.gov/Archives/edgar/data/1318605/000000000124000002/q2.htm"
Q3_URL = "https://www.sec.gov/Archives/edgar/data/1318605/000000000124000003/q3.htm"
K_URL = "https://www.sec.gov/Archives/edgar/data/1318605/000000000124000004/k.htm"


def _fact(
    *,
    metric: str,
    start: str,
    end: str,
    accession: str,
    form: str,
    filing_end: str,
    filed: str,
    url: str,
    value: int,
    concept: str = "us-gaap:Revenues",
) -> ReportedFact:
    return ReportedFact(
        metric=metric,
        period_start=date.fromisoformat(start),
        period_end=date.fromisoformat(end),
        accession=accession,
        form=form,
        filing_period_end=date.fromisoformat(filing_end),
        filing_date=date.fromisoformat(filed),
        filing_url=url,
        value=Decimal(value),
        unit="USD",
        concept=concept,
    )


def _database() -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect()
    apply_schema(connection)
    return connection


def test_two_filings_of_one_period_both_stay_stored() -> None:
    connection = _database()
    store_reported_facts(
        connection,
        [
            _fact(
                metric="total_revenue",
                start="2024-01-01",
                end="2024-03-31",
                accession="0000000001-24-000001",
                form="10-Q",
                filing_end="2024-03-31",
                filed="2024-04-23",
                url=Q1_URL,
                value=100,
            ),
            _fact(
                metric="total_revenue",
                start="2024-01-01",
                end="2024-03-31",
                accession="0000000001-24-000002",
                form="10-Q",
                filing_end="2024-06-30",
                filed="2024-07-23",
                url=Q2_URL,
                value=110,
            ),
        ],
    )
    stored = connection.execute(
        """
        SELECT accession, filing_date, filing_url, value
        FROM fact_with_source
        ORDER BY filing_date
        """
    ).fetchall()
    assert stored == [
        ("0000000001-24-000001", date(2024, 4, 23), Q1_URL, Decimal("100.0000")),
        ("0000000001-24-000002", date(2024, 7, 23), Q2_URL, Decimal("110.0000")),
    ]
    early = connection.execute(
        "SELECT accession, value FROM fact_as_of(DATE '2024-05-01')"
    ).fetchone()
    later = connection.execute(
        "SELECT accession, value FROM fact_as_of(DATE '2024-08-01')"
    ).fetchone()
    assert early == ("0000000001-24-000001", Decimal("100.0000"))
    assert later == ("0000000001-24-000002", Decimal("110.0000"))
    assert connection.execute("SELECT count(*) FROM fact").fetchone() == (2,)


def test_later_comparative_does_not_replace_the_first_reported_quarter() -> None:
    connection = _database()
    store_reported_facts(
        connection,
        [
            _fact(
                metric="total_revenue",
                start="2024-01-01",
                end="2024-03-31",
                accession="0000000001-24-000001",
                form="10-Q",
                filing_end="2024-03-31",
                filed="2024-04-23",
                url=Q1_URL,
                value=100,
            ),
            _fact(
                metric="total_revenue",
                start="2024-01-01",
                end="2024-03-31",
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
    actual = connection.execute(
        "SELECT value, accession, basis FROM quarter_actual WHERE quarter = '2024-Q1'"
    ).fetchone()
    assert actual == (Decimal("100.0000"), "0000000001-24-000001", "first_reported")
    assert connection.execute("SELECT count(*) FROM fact").fetchone() == (2,)


def test_q4_comes_from_the_10k_minus_the_first_three_quarters() -> None:
    connection = _database()
    store_reported_facts(
        connection,
        [
            _fact(
                metric="total_revenue",
                start="2024-01-01",
                end="2024-03-31",
                accession="0000000001-24-000001",
                form="10-Q",
                filing_end="2024-03-31",
                filed="2024-04-23",
                url=Q1_URL,
                value=10,
            ),
            _fact(
                metric="total_revenue",
                start="2024-04-01",
                end="2024-06-30",
                accession="0000000001-24-000002",
                form="10-Q",
                filing_end="2024-06-30",
                filed="2024-07-23",
                url=Q2_URL,
                value=20,
            ),
            _fact(
                metric="total_revenue",
                start="2024-07-01",
                end="2024-09-30",
                accession="0000000001-24-000003",
                form="10-Q",
                filing_end="2024-09-30",
                filed="2024-10-23",
                url=Q3_URL,
                value=30,
            ),
            _fact(
                metric="total_revenue",
                start="2024-01-01",
                end="2024-12-31",
                accession="0000000001-24-000004",
                form="10-K",
                filing_end="2024-12-31",
                filed="2025-01-29",
                url=K_URL,
                value=100,
            ),
            _fact(
                metric="total_revenue",
                start="2024-10-01",
                end="2024-12-31",
                accession="0000000001-24-000004",
                form="10-K",
                filing_end="2024-12-31",
                filed="2025-01-29",
                url=K_URL,
                value=99,
            ),
        ],
    )
    assemble_quarter_actuals(connection)
    q4 = connection.execute(
        """
        SELECT value, accession, basis
        FROM quarter_actual
        WHERE quarter = '2024-Q4' AND metric = 'total_revenue'
        """
    ).fetchone()
    assert q4 == (Decimal("40.0000"), "0000000001-24-000004", "derived_q4")


def test_cash_flow_quarters_are_decumulated_and_q4_is_derived() -> None:
    connection = _database()
    metric = "net_cash_from_operating_activities"
    concept = "us-gaap:NetCashProvidedByUsedInOperatingActivities"
    store_reported_facts(
        connection,
        [
            _fact(
                metric=metric,
                start="2024-01-01",
                end="2024-03-31",
                accession="0000000001-24-000001",
                form="10-Q",
                filing_end="2024-03-31",
                filed="2024-04-23",
                url=Q1_URL,
                value=10,
                concept=concept,
            ),
            _fact(
                metric=metric,
                start="2024-01-01",
                end="2024-06-30",
                accession="0000000001-24-000002",
                form="10-Q",
                filing_end="2024-06-30",
                filed="2024-07-23",
                url=Q2_URL,
                value=25,
                concept=concept,
            ),
            _fact(
                metric=metric,
                start="2024-01-01",
                end="2024-09-30",
                accession="0000000001-24-000003",
                form="10-Q",
                filing_end="2024-09-30",
                filed="2024-10-23",
                url=Q3_URL,
                value=40,
                concept=concept,
            ),
            _fact(
                metric=metric,
                start="2024-01-01",
                end="2024-12-31",
                accession="0000000001-24-000004",
                form="10-K",
                filing_end="2024-12-31",
                filed="2025-01-29",
                url=K_URL,
                value=60,
                concept=concept,
            ),
        ],
    )
    assemble_quarter_actuals(connection)
    rows = connection.execute(
        """
        SELECT quarter, value, basis
        FROM quarter_actual
        WHERE metric = ?
        ORDER BY quarter
        """,
        [metric],
    ).fetchall()
    assert rows == [
        ("2024-Q1", Decimal("10.0000"), "first_reported"),
        ("2024-Q2", Decimal("15.0000"), "decumulated"),
        ("2024-Q3", Decimal("15.0000"), "decumulated"),
        ("2024-Q4", Decimal("20.0000"), "derived_q4"),
    ]


def test_companyfacts_keeps_both_filings_and_skips_member_tags() -> None:
    companyfacts = {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {
                                "start": "2024-01-01",
                                "end": "2024-03-31",
                                "val": 100,
                                "accn": "0001628280-24-000001",
                                "form": "10-Q",
                                "filed": "2024-04-23",
                                "frame": "CY2024Q1",
                            },
                            {
                                "start": "2024-01-01",
                                "end": "2024-03-31",
                                "val": 110,
                                "accn": "0001628280-24-000002",
                                "form": "10-Q",
                                "filed": "2024-07-23",
                            },
                        ]
                    }
                }
            }
        }
    }
    submissions = {
        "filings": {
            "recent": {
                "accessionNumber": [
                    "0001628280-24-000001",
                    "0001628280-24-000002",
                ],
                "form": ["10-Q", "10-Q"],
                "filingDate": ["2024-04-23", "2024-07-23"],
                "reportDate": ["2024-03-31", "2024-06-30"],
                "primaryDocument": ["tsla-q1.htm", "tsla-q2.htm"],
            }
        }
    }
    reported = facts_from_companyfacts(companyfacts, submissions, load_xbrl_map())
    revenue = [fact for fact in reported if fact.metric == "total_revenue"]
    assert len(revenue) == 2
    assert {fact.value for fact in revenue} == {Decimal(100), Decimal(110)}
    assert {fact.filing_url for fact in revenue} == {
        "https://www.sec.gov/Archives/edgar/data/1318605/000162828024000001/tsla-q1.htm",
        "https://www.sec.gov/Archives/edgar/data/1318605/000162828024000002/tsla-q2.htm",
    }
    assert [fact for fact in reported if fact.metric == "automotive_sales"] == []
    connection = _database()
    store_reported_facts(connection, reported)
    assemble_quarter_actuals(connection)
    actual = connection.execute(
        "SELECT value, basis FROM quarter_actual WHERE metric = 'total_revenue'"
    ).fetchone()
    assert actual == (Decimal("100.0000"), "first_reported")
    assert connection.execute("SELECT count(*) FROM fact").fetchone() == (2,)
