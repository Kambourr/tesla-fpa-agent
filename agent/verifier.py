"""Check every narration claim against the fact sheet, in code.

The verifier never calls a model and never edits a claim. It does not rewrite
a claim's ``value``, ``unit``, ``metric`` or ``period``, and it does not touch
the sentence the claim points at. A mismatch is reported with the expected
value so the reader can see it. It is never silently corrected.

Statuses:

- ``verified``: the key and period exist and the value matches after unit
  normalization, within tolerance.
- ``flagged``: the fact exists but the value or unit does not match. The
  result carries the expected fact value.
- ``unsupported``: no fact has that key, or the key has no value for that
  period.

Tolerances (brief section 4):

- USD and USD_per_unit: within 0.5% of the absolute expected value. An
  expected value of exactly 0 needs an exact 0.
- percent: within 0.1 percentage points.
- units: exact after normalization. The one exception is a claim written in
  thousands (for example ``497.1`` with unit ``thousand vehicles``), which is
  a rounded figure. It matches when the expected value, rounded to the claim's
  stated precision, equals the claim.

Signs matter. Variances are written with a sign, so a claim of ``1.2`` for an
expected ``-1.2`` is flagged. There is no exception. The model must write
signed values for variances. A nonzero claim and a nonzero expected value
with opposite signs are always flagged, even when the magnitude is inside the
tolerance.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import StrEnum

from agent.fact_sheet import PERCENT, UNITS, USD, USD_PER_UNIT, Fact, lookup
from agent.narrative import Claim

CURRENCY_TOLERANCE = Decimal("0.005")
PERCENT_TOLERANCE = Decimal("0.1")

_USD_MULTIPLIERS: dict[str, int] = {
    "usd": 1,
    "dollars": 1,
    "usd thousand": 1_000,
    "thousand": 1_000,
    "k": 1_000,
    "usd million": 1_000_000,
    "million": 1_000_000,
    "m": 1_000_000,
    "mm": 1_000_000,
    "usd billion": 1_000_000_000,
    "billion": 1_000_000_000,
    "b": 1_000_000_000,
    "bn": 1_000_000_000,
}
_PERCENT_MULTIPLIERS: dict[str, int] = {
    "percent": 1,
    "%": 1,
    "pct": 1,
    "percentage points": 1,
    "pp": 1,
    "points": 1,
}
_UNIT_MULTIPLIERS: dict[str, int] = {
    "units": 1,
    "vehicles": 1,
    "deliveries": 1,
    "cars": 1,
    "thousand vehicles": 1_000,
    "thousand units": 1_000,
}
_USD_PER_UNIT_MULTIPLIERS: dict[str, int] = {
    "usd per vehicle": 1,
    "usd per unit": 1,
    "usd_per_unit": 1,
    "usd thousand per vehicle": 1_000,
}
_TABLES: dict[str, dict[str, int]] = {
    USD: _USD_MULTIPLIERS,
    PERCENT: _PERCENT_MULTIPLIERS,
    UNITS: _UNIT_MULTIPLIERS,
    USD_PER_UNIT: _USD_PER_UNIT_MULTIPLIERS,
}


class Status(StrEnum):
    VERIFIED = "verified"
    FLAGGED = "flagged"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class ClaimResult:
    claim: Claim
    status: Status
    expected: Decimal | None
    expected_unit: str | None
    normalized: Decimal | None
    source: str | None
    source_url: str | None
    reason: str


def normalize(value: float | Decimal, unit: str, fact_unit: str) -> Decimal | None:
    """Convert a claim's value and unit string into ``fact_unit``.

    Returns None when the unit is not compatible with the fact unit, or when
    the value is not a finite number. The unit string is case-insensitive and
    may use ``$`` in place of ``USD``.
    """
    number = _decimal(value)
    table = _TABLES.get(fact_unit)
    if number is None or table is None:
        return None
    multiplier = table.get(_canonical_unit(unit))
    if multiplier is None:
        return None
    return number * multiplier


def verify_claim(claim: Claim, facts_index: dict[tuple[str, str], Fact]) -> ClaimResult:
    """Check one claim against the indexed fact sheet."""
    fact = facts_index.get((claim.metric, claim.period))
    if fact is None:
        if any(key == claim.metric for key, _ in facts_index):
            reason = f"fact '{claim.metric}' has no value for period '{claim.period}'"
        else:
            reason = f"no fact with key '{claim.metric}'"
        return _result(claim, Status.UNSUPPORTED, reason)

    base = {"source": fact.source, "source_url": fact.source_url, "expected_unit": fact.unit}
    expected = fact.value
    if not math.isfinite(claim.value):
        return _result(
            claim,
            Status.FLAGGED,
            "claim value is not a finite number",
            expected=expected,
            **base,
        )
    normalized = normalize(claim.value, claim.unit, fact.unit)
    if normalized is None:
        return _result(
            claim,
            Status.FLAGGED,
            f"unit '{claim.unit}' does not match '{fact.unit}' for {claim.metric}",
            expected=expected,
            **base,
        )

    if normalized and expected and (normalized < 0) != (expected < 0):
        return _result(
            claim,
            Status.FLAGGED,
            f"sign differs: claim {normalized}, expected {expected}",
            expected=expected,
            normalized=normalized,
            **base,
        )

    ok, detail = _within_tolerance(claim, normalized, fact)
    status = Status.VERIFIED if ok else Status.FLAGGED
    if ok:
        reason = f"matches expected {expected} ({detail})"
    else:
        reason = f"value {normalized} does not match expected {expected} ({detail})"
    return _result(
        claim,
        status,
        reason,
        expected=expected,
        normalized=normalized,
        **base,
    )


def verify_claims(claims: Iterable[Claim], facts: tuple[Fact, ...]) -> tuple[ClaimResult, ...]:
    """Verify every claim against one fact sheet, in the order given."""
    index = lookup(facts)
    return tuple(verify_claim(claim, index) for claim in claims)


def summarize(results: Iterable[ClaimResult]) -> dict[str, int]:
    """Count results by status, plus a ``total``."""
    counts = {status.value: 0 for status in Status}
    total = 0
    for result in results:
        counts[result.status.value] += 1
        total += 1
    counts["total"] = total
    return counts


def _within_tolerance(claim: Claim, normalized: Decimal, fact: Fact) -> tuple[bool, str]:
    expected = fact.value
    if fact.unit in (USD, USD_PER_UNIT):
        if expected == 0:
            return normalized == 0, "exact zero required"
        allowed = abs(expected) * CURRENCY_TOLERANCE
        return abs(normalized - expected) <= allowed, "within 0.5% of expected"
    if fact.unit == PERCENT:
        return abs(normalized - expected) <= PERCENT_TOLERANCE, "within 0.1 percentage points"
    # units: exact, except a claim written in thousands is a rounded figure.
    multiplier = _UNIT_MULTIPLIERS.get(_canonical_unit(claim.unit), 1)
    if multiplier == 1:
        return normalized == expected, "exact match required"
    exponent = _decimal(claim.value).as_tuple().exponent
    quantum = Decimal(10) ** exponent * multiplier
    rounded = (expected / quantum).to_integral_value(rounding=ROUND_HALF_UP) * quantum
    return normalized == rounded, f"expected rounded to {quantum} units"


def _result(
    claim: Claim,
    status: Status,
    reason: str,
    *,
    expected: Decimal | None = None,
    expected_unit: str | None = None,
    normalized: Decimal | None = None,
    source: str | None = None,
    source_url: str | None = None,
) -> ClaimResult:
    return ClaimResult(
        claim=claim,
        status=status,
        expected=expected,
        expected_unit=expected_unit,
        normalized=normalized,
        source=source,
        source_url=source_url,
        reason=reason,
    )


def _canonical_unit(unit: str) -> str:
    text = unit.strip().lower().replace("$", " usd ")
    return " ".join(text.split())


def _decimal(value: float | Decimal) -> Decimal | None:
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        return None
    return number if number.is_finite() else None
