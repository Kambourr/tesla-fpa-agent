"""Store one value per metric, period, and filing, then build quarter actuals.

``fact`` keeps every filing, including a later comparative. ``quarter_actual``
is rebuilt from those rows. Q1–Q3 income lines come from that quarter's own
10-Q. Q4 and the single-quarter cash-flow lines use ``agent.quarters``.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

import duckdb

from agent.quarters import cash_flow_quarters, derive_q4
from agent.xbrl_map import XbrlMap

CIK_PATH = "1318605"
_STATEMENT_FORMS = {"10-Q", "10-K", "10-Q/A", "10-K/A"}
CASH_FLOW_METRICS = (
    "net_cash_from_operating_activities",
    "purchases_of_property_and_equipment",
)

_SINGLE_QUARTER = {
    (1, 1, 3, 31): "Q1",
    (4, 1, 6, 30): "Q2",
    (7, 1, 9, 30): "Q3",
    (10, 1, 12, 31): "Q4",
}
_YTD_END = {(3, 31): "Q1", (6, 30): "Q2", (9, 30): "Q3"}


@dataclass(frozen=True)
class ReportedFact:
    """One reported amount, already tied to the filing that carried it."""

    metric: str
    period_start: date
    period_end: date
    accession: str
    form: str
    filing_period_end: date
    filing_date: date
    filing_url: str
    value: Decimal
    unit: str
    concept: str
    member: str | None = None


def filing_archive_url(accession: str, primary_document: str) -> str:
    """SEC archive URL for one primary document. Does not fetch it."""
    compact = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{CIK_PATH}/{compact}/{primary_document}"


def facts_from_companyfacts(
    companyfacts: dict[str, Any],
    submissions: dict[str, Any],
    tag_map: XbrlMap,
) -> list[ReportedFact]:
    """Read consolidated companyfacts rows. Dimensional tags are not in that feed.

    For one filing and period, the first tag with a fact wins. A tag that
    needs a member is skipped here, because companyfacts has no dimensions.
    """
    filings = statement_filings(submissions)
    reported: list[ReportedFact] = []
    for metric, spec in tag_map.metrics.items():
        if spec.source != "xbrl":
            continue
        chosen: dict[tuple[str, str, str], tuple[str, dict[str, Any]]] = {}
        for tag in spec.tags:
            if tag.member is not None:
                continue
            taxonomy, _, local = tag.concept.partition(":")
            entries = (
                companyfacts.get("facts", {})
                .get(taxonomy, {})
                .get(local, {})
                .get("units", {})
                .get("USD", [])
            )
            grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
            for item in entries:
                if item.get("form") not in _STATEMENT_FORMS:
                    continue
                if "start" not in item or "end" not in item or "accn" not in item:
                    continue
                grouped[(item["accn"], item["start"], item["end"])].append(item)
            for key, items in grouped.items():
                if key in chosen:
                    continue
                chosen[key] = (tag.concept, _one_value(metric, items))
        for (accession, start, end), (concept, item) in chosen.items():
            filing = filings.get(accession)
            if filing is None:
                raise ValueError(f"no filing index row for {accession}")
            reported.append(
                ReportedFact(
                    metric=metric,
                    period_start=date.fromisoformat(start),
                    period_end=date.fromisoformat(end),
                    accession=accession,
                    form=filing.form,
                    filing_period_end=filing.period_end,
                    filing_date=filing.filing_date,
                    filing_url=filing.filing_url,
                    value=_decimal_value(item["val"]),
                    unit="USD",
                    concept=concept,
                    member=None,
                )
            )
    return reported


def store_reported_facts(
    connection: duckdb.DuckDBPyConnection,
    facts: list[ReportedFact],
) -> None:
    """Insert filings and facts. A second filing for the same period is another row."""
    for fact in facts:
        _upsert_filing(connection, fact)
        _insert_fact(connection, fact)


def assemble_quarter_actuals(connection: duckdb.DuckDBPyConnection) -> None:
    """Rebuild ``quarter_actual`` from ``fact``. Does not delete fact rows."""
    connection.execute("DELETE FROM quarter_actual")
    rows = [
        _StoredRow(*row)
        for row in connection.execute(
            """
            SELECT
                fact.metric,
                fact.period_start,
                fact.period_end,
                fact.value,
                fact.accession,
                filing.form,
                filing.period_end,
                filing.filing_date,
                filing.filing_url
            FROM fact
            INNER JOIN filing ON filing.accession = fact.accession
            """
        ).fetchall()
    ]
    by_metric: dict[str, list[_StoredRow]] = defaultdict(list)
    for row in rows:
        by_metric[row.metric].append(row)
    for metric, metric_rows in by_metric.items():
        if metric in CASH_FLOW_METRICS:
            _assemble_cash_flow(connection, metric, metric_rows)
        else:
            _assemble_income(connection, metric, metric_rows)


@dataclass(frozen=True)
class _Filing:
    form: str
    period_end: date
    filing_date: date
    filing_url: str


@dataclass(frozen=True)
class _StoredRow:
    metric: str
    period_start: date
    period_end: date
    value: Decimal
    accession: str
    form: str
    filing_period_end: date
    filing_date: date
    filing_url: str


def statement_filings(submissions: dict[str, Any]) -> dict[str, _Filing]:
    recent = submissions["filings"]["recent"]
    indexed: dict[str, _Filing] = {}
    accessions = recent.get("accessionNumber", [])
    for index, accession in enumerate(accessions):
        form = recent["form"][index]
        if form not in _STATEMENT_FORMS:
            continue
        primary = recent["primaryDocument"][index]
        indexed[accession] = _Filing(
            form=form,
            period_end=date.fromisoformat(recent["reportDate"][index]),
            filing_date=date.fromisoformat(recent["filingDate"][index]),
            filing_url=filing_archive_url(accession, primary),
        )
    return indexed


def _one_value(metric: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    framed = [item for item in items if item.get("frame")]
    pool = framed or items
    values = {_decimal_value(item["val"]) for item in pool}
    if len(values) > 1:
        accession = pool[0].get("accn", "")
        raise ValueError(f"{metric} has two values in filing {accession} for one period")
    return pool[0]


def _decimal_value(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float) and value == int(value):
        return Decimal(int(value))
    raise ValueError(f"fact value must be a whole number, got {value!r}")


def _upsert_filing(connection: duckdb.DuckDBPyConnection, fact: ReportedFact) -> None:
    existing = connection.execute(
        """
        SELECT form, period_end, filing_date, filing_url
        FROM filing
        WHERE accession = ?
        """,
        [fact.accession],
    ).fetchone()
    if existing is None:
        connection.execute(
            "INSERT INTO filing VALUES (?, ?, ?, ?, ?)",
            [
                fact.accession,
                fact.form,
                fact.filing_period_end,
                fact.filing_date,
                fact.filing_url,
            ],
        )
        return
    current = (existing[0], existing[1], existing[2], existing[3])
    expected = (fact.form, fact.filing_period_end, fact.filing_date, fact.filing_url)
    if current != expected:
        raise ValueError(f"filing {fact.accession} does not match an earlier row")


def _insert_fact(connection: duckdb.DuckDBPyConnection, fact: ReportedFact) -> None:
    existing = connection.execute(
        """
        SELECT value
        FROM fact
        WHERE metric = ? AND period_start = ? AND period_end = ? AND accession = ?
        """,
        [fact.metric, fact.period_start, fact.period_end, fact.accession],
    ).fetchone()
    if existing is not None:
        if Decimal(existing[0]) != fact.value:
            raise ValueError(f"{fact.metric} already has a different value in {fact.accession}")
        return
    connection.execute(
        "INSERT INTO fact VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            fact.metric,
            fact.period_start,
            fact.period_end,
            fact.accession,
            fact.value,
            fact.unit,
            fact.concept,
            fact.member,
        ],
    )


def _assemble_income(
    connection: duckdb.DuckDBPyConnection,
    metric: str,
    rows: list[_StoredRow],
) -> None:
    first: dict[str, _StoredRow] = {}
    for row in rows:
        quarter = _single_quarter(row.period_start, row.period_end)
        if quarter is None or not row.form.startswith("10-Q"):
            continue
        if row.filing_period_end != row.period_end:
            continue
        current = first.get(quarter)
        if current is None or (row.filing_date, row.accession) < (
            current.filing_date,
            current.accession,
        ):
            first[quarter] = row
    for quarter, row in first.items():
        _insert_actual(connection, quarter, metric, row, "first_reported")
    annuals = [
        row
        for row in rows
        if _is_annual(row.period_start, row.period_end)
        and row.form.startswith("10-K")
        and row.filing_period_end == row.period_end
    ]
    by_year: dict[int, _StoredRow] = {}
    for row in annuals:
        year = row.period_end.year
        current = by_year.get(year)
        if current is None or (row.filing_date, row.accession) < (
            current.filing_date,
            current.accession,
        ):
            by_year[year] = row
    for year, annual in by_year.items():
        quarters = [first.get(f"{year}-Q{number}") for number in (1, 2, 3)]
        if any(quarter is None for quarter in quarters):
            continue
        q1, q2, q3 = quarters
        assert q1 is not None and q2 is not None and q3 is not None
        derived = derive_q4(
            _whole(annual.value),
            _whole(q1.value),
            _whole(q2.value),
            _whole(q3.value),
        )
        _insert_actual_value(
            connection,
            f"{year}-Q4",
            metric,
            Decimal(derived),
            annual,
            "derived_q4",
        )


def _assemble_cash_flow(
    connection: duckdb.DuckDBPyConnection,
    metric: str,
    rows: list[_StoredRow],
) -> None:
    ytd: dict[str, _StoredRow] = {}
    for row in rows:
        quarter = _ytd_quarter(row.period_start, row.period_end)
        if quarter is None or not row.form.startswith("10-Q"):
            continue
        if row.filing_period_end != row.period_end:
            continue
        current = ytd.get(quarter)
        if current is None or (row.filing_date, row.accession) < (
            current.filing_date,
            current.accession,
        ):
            ytd[quarter] = row
    annuals: dict[int, _StoredRow] = {}
    for row in rows:
        if not _is_annual(row.period_start, row.period_end):
            continue
        if not row.form.startswith("10-K") or row.filing_period_end != row.period_end:
            continue
        year = row.period_end.year
        current = annuals.get(year)
        if current is None or (row.filing_date, row.accession) < (
            current.filing_date,
            current.accession,
        ):
            annuals[year] = row
    years = {int(label[:4]) for label in ytd} | set(annuals)
    for year in years:
        # A year still in progress has no 10-K. Its quarters de-cumulate from
        # the 10-Qs that exist, so the latest quarters are not left blank.
        q1, q2, q3 = (ytd.get(f"{year}-Q{number}") for number in (1, 2, 3))
        annual = annuals.get(year)
        if q1 is not None:
            _insert_actual_value(
                connection, f"{year}-Q1", metric, Decimal(_whole(q1.value)), q1, "first_reported"
            )
        if q1 is not None and q2 is not None:
            single = _whole(q2.value) - _whole(q1.value)
            _insert_actual_value(
                connection, f"{year}-Q2", metric, Decimal(single), q2, "decumulated"
            )
        if q2 is not None and q3 is not None:
            single = _whole(q3.value) - _whole(q2.value)
            _insert_actual_value(
                connection, f"{year}-Q3", metric, Decimal(single), q3, "decumulated"
            )
        if q1 is None or q2 is None or q3 is None or annual is None:
            continue
        amounts = cash_flow_quarters(
            _whole(q1.value),
            _whole(q2.value),
            _whole(q3.value),
            _whole(annual.value),
        )
        _insert_actual_value(
            connection,
            f"{year}-Q4",
            metric,
            Decimal(amounts.q4),
            annual,
            "derived_q4",
        )


def _insert_actual(
    connection: duckdb.DuckDBPyConnection,
    quarter: str,
    metric: str,
    row: _StoredRow,
    basis: str,
) -> None:
    _insert_actual_value(connection, quarter, metric, Decimal(row.value), row, basis)


def _insert_actual_value(
    connection: duckdb.DuckDBPyConnection,
    quarter: str,
    metric: str,
    value: Decimal,
    source: _StoredRow,
    basis: str,
) -> None:
    connection.execute(
        "INSERT INTO quarter_actual VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            quarter,
            metric,
            value,
            source.accession,
            source.filing_date,
            source.filing_url,
            basis,
        ],
    )


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


def _whole(value: Decimal) -> int:
    integral = value.to_integral_value()
    if value != integral:
        raise ValueError(f"quarter derivation needs a whole-dollar amount, got {value}")
    return int(integral)
