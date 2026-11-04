"""Forecast inputs as of the previous quarter's filing date.

Section 8 sets the cutoff: the filing date of the previous quarter's 10-Q
or 10-K. Facts are the latest stored values on that date, from
``fact_as_of``. The target quarter's deliveries and production are left
out even when that release date is on or before the cutoff.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import duckdb

_QUARTER = re.compile(r"^(\d{4})-Q([1-4])$")
_QUARTER_END = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}


class CutoffError(Exception):
    """The previous quarter has no 10-Q or 10-K to date the forecast."""


class LookaheadError(Exception):
    """An input is dated after the cutoff, or it is the target quarter."""


@dataclass(frozen=True)
class ForecastFact:
    """One metric and period as stored on the cutoff date."""

    metric: str
    period_start: date
    period_end: date
    accession: str
    filing_date: date
    filing_url: str
    value: Decimal


@dataclass(frozen=True)
class ForecastDelivery:
    """Production and deliveries for a quarter already released by the cutoff."""

    quarter: str
    production_total: int
    deliveries_total: int
    release_date: date


@dataclass(frozen=True)
class ForecastInputs:
    """Everything the forecast for one quarter is allowed to read."""

    target_quarter: str
    cutoff_date: date
    cutoff_accession: str
    facts: tuple[ForecastFact, ...]
    deliveries: tuple[ForecastDelivery, ...]


def quarter_index(label: str) -> int:
    """Turn ``2024-Q2`` into a number that orders the quarters."""
    match = _QUARTER.fullmatch(label)
    if match is None:
        raise CutoffError(f"bad quarter label {label}")
    year = int(match.group(1))
    quarter = int(match.group(2))
    return year * 4 + (quarter - 1)


def shift_quarter(label: str, offset: int) -> str:
    """Move ``label`` by ``offset`` quarters. Negative offsets go backward."""
    index = quarter_index(label) + offset
    year, remainder = divmod(index, 4)
    return f"{year}-Q{remainder + 1}"


def quarter_period_end(label: str) -> date:
    """Last calendar day of a quarter label."""
    match = _QUARTER.fullmatch(label)
    if match is None:
        raise CutoffError(f"bad quarter label {label}")
    year = int(match.group(1))
    month, day = _QUARTER_END[int(match.group(2))]
    return date(year, month, day)


def cutoff_filing(connection: duckdb.DuckDBPyConnection, target_quarter: str) -> tuple[date, str]:
    """Earliest 10-Q or 10-K filing date for the quarter before ``target_quarter``.

    An amendment does not move the cutoff later. ``fact_as_of`` then sees
    only what was filed on or before that first date.
    """
    previous = shift_quarter(target_quarter, -1)
    period_end = quarter_period_end(previous)
    row = connection.execute(
        """
        SELECT filing_date, accession
        FROM filing
        WHERE period_end = ?
          AND (form LIKE '10-Q%' OR form LIKE '10-K%')
        ORDER BY filing_date ASC, accession ASC
        LIMIT 1
        """,
        [period_end],
    ).fetchone()
    if row is None:
        raise CutoffError(f"no 10-Q or 10-K filing for {previous}")
    filing_date, accession = row
    return filing_date, accession


def load_forecast_inputs(
    connection: duckdb.DuckDBPyConnection,
    target_quarter: str,
) -> ForecastInputs:
    """Read facts and deliveries that existed on the cutoff. Nothing later."""
    quarter_index(target_quarter)
    cutoff_date, cutoff_accession = cutoff_filing(connection, target_quarter)
    fact_rows = connection.execute(
        """
        SELECT
            metric,
            period_start,
            period_end,
            accession,
            filing_date,
            filing_url,
            value
        FROM fact_as_of(?)
        ORDER BY metric, period_start, period_end, accession
        """,
        [cutoff_date],
    ).fetchall()
    delivery_rows = connection.execute(
        """
        SELECT quarter, production_total, deliveries_total, release_date
        FROM deliveries
        WHERE release_date <= ?
        ORDER BY quarter
        """,
        [cutoff_date],
    ).fetchall()
    target_index = quarter_index(target_quarter)
    deliveries = tuple(
        ForecastDelivery(
            quarter=quarter,
            production_total=int(production),
            deliveries_total=int(delivered),
            release_date=released,
        )
        for quarter, production, delivered, released in delivery_rows
        if quarter_index(quarter) < target_index
    )
    inputs = ForecastInputs(
        target_quarter=target_quarter,
        cutoff_date=cutoff_date,
        cutoff_accession=cutoff_accession,
        facts=tuple(
            ForecastFact(
                metric=metric,
                period_start=start,
                period_end=end,
                accession=accession,
                filing_date=filed,
                filing_url=url,
                value=Decimal(value),
            )
            for metric, start, end, accession, filed, url, value in fact_rows
        ),
        deliveries=deliveries,
    )
    _reject_lookahead(inputs)
    return inputs


def _reject_lookahead(inputs: ForecastInputs) -> None:
    target_index = quarter_index(inputs.target_quarter)
    for fact in inputs.facts:
        if fact.filing_date > inputs.cutoff_date:
            raise LookaheadError(
                f"{fact.metric} filing {fact.accession} is after {inputs.cutoff_date}"
            )
    for row in inputs.deliveries:
        if quarter_index(row.quarter) >= target_index:
            raise LookaheadError(
                f"{row.quarter} deliveries are not an input to {inputs.target_quarter}"
            )
        if row.release_date > inputs.cutoff_date:
            raise LookaheadError(f"{row.quarter} was released after {inputs.cutoff_date}")
