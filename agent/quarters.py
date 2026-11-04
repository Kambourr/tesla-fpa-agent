"""Quarter math for statements that are not already single quarters.

Income-statement lines in a 10-Q are single quarters. Pass those, plus the
annual 10-K figure, to ``derive_q4``.

Cash-flow lines in a 10-Q are year-to-date. Pass those to ``decumulate_ytd``,
then derive Q4 from the single quarters. Free cash flow is CFO minus capex
on those single-quarter values. Capex is the positive purchases amount.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class QuarterAmounts:
    """Single-quarter amounts for one fiscal year. Q4 may be derived."""

    q1: int
    q2: int
    q3: int
    q4: int


def derive_q4(annual: int, q1: int, q2: int, q3: int) -> int:
    """Q4 equals the annual figure minus Q1, Q2, and Q3."""
    return annual - q1 - q2 - q3


def decumulate_ytd(q1_ytd: int, q2_ytd: int, q3_ytd: int) -> tuple[int, int, int]:
    """Turn year-to-date cash-flow figures into single quarters.

    Q1 is unchanged. Q2 is Q2 year-to-date minus Q1. Q3 is Q3 year-to-date
    minus Q2 year-to-date.
    """
    return (q1_ytd, q2_ytd - q1_ytd, q3_ytd - q2_ytd)


def cash_flow_quarters(
    q1_ytd: int,
    q2_ytd: int,
    q3_ytd: int,
    annual: int,
) -> QuarterAmounts:
    """De-cumulate Q1–Q3, then set Q4 to the annual figure minus those quarters."""
    q1, q2, q3 = decumulate_ytd(q1_ytd, q2_ytd, q3_ytd)
    return QuarterAmounts(q1=q1, q2=q2, q3=q3, q4=derive_q4(annual, q1, q2, q3))


def free_cash_flow(operating_cash_flow: int, capex: int) -> int:
    """Free cash flow is CFO minus capex. ``capex`` is a positive purchase amount."""
    return operating_cash_flow - capex


def quarterly_free_cash_flow(cfo: QuarterAmounts, capex: QuarterAmounts) -> QuarterAmounts:
    """Free cash flow for each quarter, from the quarterly CFO and capex values."""
    return QuarterAmounts(
        q1=free_cash_flow(cfo.q1, capex.q1),
        q2=free_cash_flow(cfo.q2, capex.q2),
        q3=free_cash_flow(cfo.q3, capex.q3),
        q4=free_cash_flow(cfo.q4, capex.q4),
    )
