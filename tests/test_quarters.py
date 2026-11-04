"""Q4 derivation and year-to-date cash-flow de-cumulation.

The figures below are arithmetic fixtures. They are not Tesla's reported results.
"""

from agent.quarters import (
    cash_flow_quarters,
    decumulate_ytd,
    derive_q4,
    quarterly_free_cash_flow,
)

# Operating cash flow, year-to-date through Q1, Q2, Q3, then the 10-K annual figure.
CFO_YTD = (100, 250, 400, 700)
# Purchases of property and equipment, same shape. Positive amounts.
CAPEX_YTD = (40, 90, 160, 250)


def test_q4_equals_annual_minus_q1_through_q3() -> None:
    annual, q1, q2, q3 = 1000, 200, 250, 300
    assert derive_q4(annual, q1, q2, q3) == annual - q1 - q2 - q3
    assert derive_q4(annual, q1, q2, q3) == 250


def test_operating_cash_flow_decumulates_to_single_quarters() -> None:
    q1_ytd, q2_ytd, q3_ytd, annual = CFO_YTD
    q1, q2, q3 = decumulate_ytd(q1_ytd, q2_ytd, q3_ytd)
    assert q1 == q1_ytd
    assert q2 == q2_ytd - q1_ytd
    assert q3 == q3_ytd - q2_ytd
    quarters = cash_flow_quarters(q1_ytd, q2_ytd, q3_ytd, annual)
    assert (quarters.q1, quarters.q2, quarters.q3) == (100, 150, 150)
    assert quarters.q4 == annual - quarters.q1 - quarters.q2 - quarters.q3
    assert quarters.q4 == 300
    assert quarters.q1 + quarters.q2 + quarters.q3 + quarters.q4 == annual


def test_capex_decumulates_to_single_quarters() -> None:
    q1_ytd, q2_ytd, q3_ytd, annual = CAPEX_YTD
    q1, q2, q3 = decumulate_ytd(q1_ytd, q2_ytd, q3_ytd)
    assert (q1, q2, q3) == (40, 50, 70)
    quarters = cash_flow_quarters(q1_ytd, q2_ytd, q3_ytd, annual)
    assert quarters.q4 == annual - q1 - q2 - q3
    assert quarters.q4 == 90
    assert quarters.q1 + quarters.q2 + quarters.q3 + quarters.q4 == annual


def test_free_cash_flow_is_quarterly_cfo_minus_quarterly_capex() -> None:
    cfo = cash_flow_quarters(*CFO_YTD)
    capex = cash_flow_quarters(*CAPEX_YTD)
    fcf = quarterly_free_cash_flow(cfo, capex)
    assert fcf.q1 == cfo.q1 - capex.q1
    assert fcf.q2 == cfo.q2 - capex.q2
    assert fcf.q3 == cfo.q3 - capex.q3
    assert fcf.q4 == cfo.q4 - capex.q4
    assert (fcf.q1, fcf.q2, fcf.q3, fcf.q4) == (60, 100, 80, 210)


def test_a_year_to_date_decline_stays_a_negative_single_quarter() -> None:
    q1, q2, q3 = decumulate_ytd(80, 50, 90)
    assert (q1, q2, q3) == (80, -30, 40)
    assert derive_q4(100, q1, q2, q3) == 10
