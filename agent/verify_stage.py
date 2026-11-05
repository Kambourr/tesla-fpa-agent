"""The per-quarter verification report: claims, keyword guard, and restatements.

``verify_quarter`` reads the stored narration for a quarter, checks it with
``agent.review.review_draft`` (the same code the ``narrate`` command runs), looks
for later restatements, and replaces the quarter's ``verification`` row. It
never calls a model and never writes to ``narrative``, ``quarter_actual`` or
``fact``.

``restatements`` compares each first-reported income-statement actual with the
single-quarter values that later filings carry for the same period. Cash-flow
lines are skipped: the filings report them year to date, and the quarters are
de-cumulated, so no single-quarter filing value exists to compare. Q4 is skipped
too, because it is derived from the 10-K and no filing reports a single Q4.

``reasked`` is False in every report. The narrative table does not store whether
the model was re-asked, so there is nothing to read back.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import duckdb

from agent.actuals import CASH_FLOW_METRICS
from agent.fact_sheet import Fact, backtest_facts, quarter_facts
from agent.keyword_guard import GuardHit
from agent.model_stage import StageError
from agent.narrative import NarrativeDraft
from agent.review import LocatedResult, review_draft
from agent.verifier import Status

# Start and end of each quarter's single-quarter period, as (month, day) pairs.
_QUARTER_SPANS: dict[int, tuple[tuple[int, int], tuple[int, int]]] = {
    1: ((1, 1), (3, 31)),
    2: ((4, 1), (6, 30)),
    3: ((7, 1), (9, 30)),
    4: ((10, 1), (12, 31)),
}


@dataclass(frozen=True)
class VerificationReport:
    quarter: str
    latest: bool
    verified: int
    flagged: int
    unsupported: int
    total: int
    guard_hits: tuple[GuardHit, ...]
    issues: tuple[str, ...]
    results: tuple[LocatedResult, ...]
    restatements: tuple[dict[str, Any], ...]
    reasked: bool


def restatements(connection: duckdb.DuckDBPyConnection, quarter: str) -> list[dict[str, Any]]:
    """Later filings that restate a quarter's first-reported single-quarter value.

    Only ``first_reported`` income-statement actuals are compared. A row counts when its
    filing is dated after the first-reported filing and its value differs. Rows are not
    changed: ``quarter_actual`` keeps the first-reported value.
    """
    year, number = _split_quarter(quarter)
    (start_month, start_day), (end_month, end_day) = _QUARTER_SPANS[number]
    start = date(year, start_month, start_day)
    end = date(year, end_month, end_day)
    firsts = connection.execute(
        """
        SELECT metric, value, filing_date FROM quarter_actual
        WHERE quarter = ? AND basis = 'first_reported'
        ORDER BY metric
        """,
        [quarter],
    ).fetchall()
    found: list[dict[str, Any]] = []
    for metric, first_value, first_filed in firsts:
        if metric in CASH_FLOW_METRICS:
            continue
        later = connection.execute(
            """
            SELECT fact.value, fact.accession, filing.filing_date
            FROM fact
            INNER JOIN filing ON filing.accession = fact.accession
            WHERE fact.metric = ? AND fact.period_start = ? AND fact.period_end = ?
              AND filing.filing_date > ?
            ORDER BY filing.filing_date, fact.accession
            """,
            [metric, start, end, first_filed],
        ).fetchall()
        for later_value, accession, filed in later:
            if Decimal(later_value) == Decimal(first_value):
                continue
            found.append(
                {
                    "metric": metric,
                    "first_reported": Decimal(first_value),
                    "later_value": Decimal(later_value),
                    "later_accession": accession,
                    "later_filing_date": filed,
                }
            )
    return found


def verify_quarter(
    connection: duckdb.DuckDBPyConnection,
    quarter: str,
    *,
    latest: bool,
) -> VerificationReport:
    """Check the stored narration for one quarter and replace its verification row.

    ``latest`` must match how the narration was made: the latest quarter's draft
    carries the ten answers and is checked against the backtest sheet too.
    Raises ``StageError`` when the quarter has no stored narration.
    """
    draft = NarrativeDraft.model_validate_json(_stored_payload(connection, quarter))
    facts: tuple[Fact, ...] = tuple(quarter_facts(connection, quarter))
    if latest:
        facts += tuple(backtest_facts(connection))
    review = review_draft(draft, facts, quarter=quarter, latest=latest)
    report = VerificationReport(
        quarter=quarter,
        latest=latest,
        verified=review.counts["verified"],
        flagged=review.counts["flagged"],
        unsupported=review.counts["unsupported"],
        total=review.counts["total"],
        guard_hits=review.guard_hits,
        issues=review.issues,
        results=review.results,
        restatements=tuple(restatements(connection, quarter)),
        reasked=False,
    )
    _store(connection, report)
    return report


def verify_all(connection: duckdb.DuckDBPyConnection) -> list[VerificationReport]:
    """Verify each published backtest quarter with a forecast, oldest first.

    The same quarters as ``agent.narrate.narrate_all``. The latest one gets the
    backtest facts. Every quarter's narration is checked before anything is
    written, so a missing narration writes no reports.
    """
    rows = connection.execute(
        """
        SELECT quarter FROM published_quarter
        WHERE kind = 'backtest' AND has_forecast
        ORDER BY quarter
        """
    ).fetchall()
    quarters = [row[0] for row in rows]
    if not quarters:
        raise StageError("no published quarter has a forecast. Run `python -m agent model` first.")
    missing = [quarter for quarter in quarters if not _has_narration(connection, quarter)]
    if missing:
        raise StageError(
            f"no stored narration for {', '.join(missing)}. Run `python -m agent narrate` first."
        )
    latest = quarters[-1]
    return [verify_quarter(connection, quarter, latest=quarter == latest) for quarter in quarters]


def format_report(report: VerificationReport) -> str:
    """Plain text: one summary line, then one line per problem found."""
    tail = [_guard_text(report), _restatement_text(report)]
    if report.issues:
        count = len(report.issues)
        tail.append(f"{count} validation issue{'' if count == 1 else 's'}")
    lines = [
        f"{report.quarter}: {report.verified} of {report.total} figures verified, "
        f"{report.flagged} flagged, {report.unsupported} unsupported; " + "; ".join(tail) + "."
    ]
    if report.reasked:
        lines.append("  The model was re-asked once with the errors; this is its second draft.")
    for item in report.results:
        result = item.result
        claim = result.claim
        where = f"{item.location}, sentence {claim.sentence_ref}"
        if result.status is Status.FLAGGED:
            lines.append(
                f"  flagged: {where}: wrote {_plain(claim.value)} {claim.unit} for "
                f"{claim.metric} ({claim.period}); fact sheet has {_plain(result.expected)} "
                f"{result.expected_unit}."
            )
        elif result.status is Status.UNSUPPORTED:
            lines.append(
                f"  unsupported: {where}: {claim.metric} for {claim.period} is not on the "
                "fact sheet."
            )
    for hit in report.guard_hits:
        lines.append(f"  keyword guard: '{hit.phrase}' in {hit.text_kind}.")
    for issue in report.issues:
        lines.append(f"  issue: {issue}")
    for found in report.restatements:
        lines.append(
            f"  restated: {found['metric']} for {report.quarter}: first reported "
            f"{_plain(found['first_reported'])}, later {_plain(found['later_value'])} "
            f"(filed {found['later_filing_date']}, {found['later_accession']}). "
            "Actuals keep the first-reported value."
        )
    return "\n".join(lines)


def _store(connection: duckdb.DuckDBPyConnection, report: VerificationReport) -> None:
    connection.execute(
        """
        INSERT OR REPLACE INTO verification (
            quarter, verified, flagged, unsupported, total, guard_hits, issues,
            claims, restatements, reasked, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            report.quarter,
            report.verified,
            report.flagged,
            report.unsupported,
            report.total,
            json.dumps([_hit_row(hit) for hit in report.guard_hits]),
            json.dumps(list(report.issues)),
            json.dumps([_claim_row(item) for item in report.results]),
            json.dumps(list(report.restatements), default=_json_default),
            report.reasked,
            datetime.now(UTC).replace(tzinfo=None),
        ],
    )


def _stored_payload(connection: duckdb.DuckDBPyConnection, quarter: str) -> str:
    row = connection.execute(
        "SELECT payload FROM narrative WHERE quarter = ?", [quarter]
    ).fetchone()
    if row is None:
        raise StageError(f"no stored narration for {quarter}. Run `python -m agent narrate` first.")
    return str(row[0])


def _has_narration(connection: duckdb.DuckDBPyConnection, quarter: str) -> bool:
    row = connection.execute(
        "SELECT count(*) FROM narrative WHERE quarter = ?", [quarter]
    ).fetchone()
    return row is not None and row[0] > 0


def _split_quarter(quarter: str) -> tuple[int, int]:
    year_text, _, label = quarter.partition("-Q")
    if not (year_text.isdigit() and label in {"1", "2", "3", "4"}):
        raise ValueError(f"not a quarter label: {quarter!r}")
    return int(year_text), int(label)


def _guard_text(report: VerificationReport) -> str:
    count = len(report.guard_hits)
    if count == 0:
        return "keyword guard clean"
    return f"keyword guard {count} hit{'' if count == 1 else 's'}"


def _restatement_text(report: VerificationReport) -> str:
    count = len(report.restatements)
    if count == 0:
        return "no later restatements"
    metrics = ", ".join(sorted({str(found["metric"]) for found in report.restatements}))
    noun = "restatement" if count == 1 else "restatements"
    return f"{count} later {noun} noted ({metrics})"


def _hit_row(hit: GuardHit) -> dict[str, Any]:
    return {"text_kind": hit.text_kind, "phrase": hit.phrase, "start": hit.start, "end": hit.end}


def _claim_row(item: LocatedResult) -> dict[str, Any]:
    result = item.result
    claim = result.claim
    return {
        "location": item.location,
        "metric": claim.metric,
        "period": claim.period,
        "value": claim.value if math.isfinite(claim.value) else str(claim.value),
        "unit": claim.unit,
        "sentence_ref": claim.sentence_ref,
        "status": result.status.value,
        "expected": None if result.expected is None else str(result.expected),
        "expected_unit": result.expected_unit,
        "source": result.source,
        "source_url": result.source_url,
        "reason": result.reason,
    }


def _json_default(value: object) -> str:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"not JSON serializable: {type(value).__name__}")


def _plain(value: float | Decimal | None) -> str:
    """A number without exponent notation, for report text."""
    if value is None:
        return "(none)"
    return format(Decimal(str(value)).normalize(), "f")
