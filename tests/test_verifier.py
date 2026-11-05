"""The verifier checks claims against facts in code, with no network and no model."""

from decimal import Decimal

import pytest

from agent.fact_sheet import PERCENT, UNITS, USD, USD_PER_UNIT, Fact, lookup, quarter_facts
from agent.model_stage import run_model, run_variance
from agent.narrative import Claim
from agent.verifier import Status, normalize, summarize, verify_claim, verify_claims
from pipeline_fixture import build_database

QUARTER = "2026-Q3"
PRIOR = "2026-Q2"


def fact(key: str, value: str, unit: str, period: str = QUARTER) -> Fact:
    return Fact(key, period, Decimal(value), unit, "test source", "https://example.test/f")


def claim(metric: str, value: float, unit: str, period: str = QUARTER) -> Claim:
    return Claim(metric=metric, period=period, value=value, unit=unit, sentence_ref="s1")


def check(c: Claim, *facts: Fact):
    return verify_claim(c, lookup(tuple(facts)))


def test_wrong_number_is_flagged_with_the_expected_value() -> None:
    revenue = fact("actual.total_revenue", "1500000000", USD)
    result = check(claim("actual.total_revenue", 1.9, "USD billion"), revenue)
    assert result.status is Status.FLAGGED
    assert result.expected == Decimal("1500000000")
    assert result.expected_unit == USD
    assert result.normalized == Decimal("1900000000")
    assert result.source == "test source"
    assert result.source_url == "https://example.test/f"


def test_billion_claim_matches_full_dollars() -> None:
    revenue = fact("actual.total_revenue", "1500000000", USD)
    assert (
        check(claim("actual.total_revenue", 1.5, "USD billion"), revenue).status is Status.VERIFIED
    )
    assert (
        check(claim("actual.total_revenue", 1500000000, "USD"), revenue).status is Status.VERIFIED
    )


def test_billion_claim_that_is_off_by_a_tenth_is_flagged() -> None:
    revenue = fact("actual.total_revenue", "1500000000", USD)
    assert (
        check(claim("actual.total_revenue", 1.6, "USD billion"), revenue).status is Status.FLAGGED
    )


def test_currency_tolerance_is_half_a_percent() -> None:
    revenue = fact("actual.total_revenue", "1000000000", USD)
    assert (
        check(claim("actual.total_revenue", 1.004, "USD billion"), revenue).status
        is Status.VERIFIED
    )
    assert (
        check(claim("actual.total_revenue", 1.006, "USD billion"), revenue).status is Status.FLAGGED
    )


def test_zero_expected_currency_needs_exact_zero() -> None:
    zero = fact("variance.total_revenue", "0", USD)
    assert check(claim("variance.total_revenue", 0, "USD"), zero).status is Status.VERIFIED
    assert check(claim("variance.total_revenue", 0.001, "USD"), zero).status is Status.FLAGGED


def test_percent_tolerance_is_a_tenth_of_a_point() -> None:
    margin = fact("actual.gross_margin", "18.2", PERCENT)
    assert check(claim("actual.gross_margin", 18.24, "percent"), margin).status is Status.VERIFIED
    assert check(claim("actual.gross_margin", 18.35, "percent"), margin).status is Status.FLAGGED


def test_percentage_points_unit_works() -> None:
    margin = fact("actual.gross_margin", "18.2", PERCENT)
    assert check(claim("actual.gross_margin", 18.24, "pp"), margin).status is Status.VERIFIED
    assert check(claim("actual.gross_margin", 18.2, "%"), margin).status is Status.VERIFIED


def test_unit_counts_must_match_exactly() -> None:
    deliveries = fact("actual.deliveries", "497099", UNITS)
    assert check(claim("actual.deliveries", 497099, "units"), deliveries).status is Status.VERIFIED
    assert check(claim("actual.deliveries", 497100, "units"), deliveries).status is Status.FLAGGED


def test_thousands_of_vehicles_is_a_rounded_figure() -> None:
    deliveries = fact("actual.deliveries", "497099", UNITS)
    assert (
        check(claim("actual.deliveries", 497.1, "thousand vehicles"), deliveries).status
        is Status.VERIFIED
    )
    assert (
        check(claim("actual.deliveries", 497.2, "thousand vehicles"), deliveries).status
        is Status.FLAGGED
    )


def test_unknown_key_is_unsupported() -> None:
    result = check(claim("actual.bananas", 1, "USD"), fact("actual.total_revenue", "1", USD))
    assert result.status is Status.UNSUPPORTED
    assert "actual.bananas" in result.reason
    assert result.expected is None


def test_known_key_with_wrong_period_is_unsupported() -> None:
    revenue = fact("actual.total_revenue", "1500000000", USD, period=PRIOR)
    result = check(claim("actual.total_revenue", 1.5, "USD billion", period=QUARTER), revenue)
    assert result.status is Status.UNSUPPORTED
    assert QUARTER in result.reason
    assert result.expected is None


def test_incompatible_unit_is_flagged_with_expected_value() -> None:
    revenue = fact("actual.total_revenue", "1500000000", USD)
    result = check(claim("actual.total_revenue", 15, "percent"), revenue)
    assert result.status is Status.FLAGGED
    assert "does not match" in result.reason
    assert result.expected == Decimal("1500000000")
    assert result.normalized is None


def test_negative_variance_with_positive_claim_is_flagged() -> None:
    variance = fact("variance.total_revenue", "-1200000000", USD)
    result = check(claim("variance.total_revenue", 1.2, "USD billion"), variance)
    assert result.status is Status.FLAGGED
    assert "sign" in result.reason
    assert result.expected == Decimal("-1200000000")


def test_sign_mismatch_is_flagged_even_inside_the_tolerance() -> None:
    small = fact("variance_pct.gross_margin", "-0.05", PERCENT)
    assert (
        check(claim("variance_pct.gross_margin", 0.05, "percent"), small).status is Status.FLAGGED
    )
    assert (
        check(claim("variance_pct.gross_margin", -0.05, "percent"), small).status is Status.VERIFIED
    )


def test_negative_variance_with_negative_claim_passes() -> None:
    variance = fact("variance.total_revenue", "-1200000000", USD)
    assert (
        check(claim("variance.total_revenue", -1.2, "USD billion"), variance).status
        is Status.VERIFIED
    )


def test_normalize_handles_case_dollar_signs_and_float_artifacts() -> None:
    assert normalize(0.1, "USD", USD) == Decimal("0.1")
    assert normalize(1.5, "$ BILLION", USD) == Decimal("1500000000")
    assert normalize(2, "$", USD) == Decimal("2")
    assert normalize(3, "Usd Million", USD) == Decimal("3000000")
    assert normalize(4, "mm", USD) == Decimal("4000000")
    assert normalize(5, "thousand", USD) == Decimal("5000")
    assert normalize(6, "k", USD) == Decimal("6000")
    assert normalize(7, "bn", USD) == Decimal("7000000000")


def test_normalize_unit_counts_and_per_unit_values() -> None:
    assert normalize(12, "vehicles", UNITS) == Decimal("12")
    assert normalize(12, "Cars", UNITS) == Decimal("12")
    assert normalize(1.5, "thousand units", UNITS) == Decimal("1500")
    assert normalize(42.3, "USD per vehicle", USD_PER_UNIT) == Decimal("42.3")
    assert normalize(42.3, "$ per vehicle", USD_PER_UNIT) == Decimal("42.3")
    assert normalize(42.3, "usd_per_unit", USD_PER_UNIT) == Decimal("42.3")
    assert normalize(42.3, "usd thousand per vehicle", USD_PER_UNIT) == Decimal("42300")


def test_normalize_returns_none_for_incompatible_units() -> None:
    assert normalize(1, "percent", USD) is None
    assert normalize(1, "USD", PERCENT) is None
    assert normalize(1, "USD", UNITS) is None
    assert normalize(1, "USD", USD_PER_UNIT) is None
    assert normalize(1, "bananas", USD) is None
    assert normalize(float("nan"), "USD", USD) is None


def test_non_finite_claim_value_is_flagged() -> None:
    revenue = fact("actual.total_revenue", "1500000000", USD)
    result = check(claim("actual.total_revenue", float("inf"), "USD"), revenue)
    assert result.status is Status.FLAGGED
    assert "finite" in result.reason


def test_verify_claims_keeps_order_and_summarize_counts() -> None:
    facts = (
        fact("actual.total_revenue", "1500000000", USD),
        fact("actual.deliveries", "497099", UNITS),
        fact("actual.gross_margin", "18.2", PERCENT),
    )
    claims = (
        claim("actual.total_revenue", 1.5, "USD billion"),
        claim("actual.deliveries", 497100, "units"),
        claim("actual.gross_margin", 18.24, "percent"),
        claim("actual.bananas", 1, "USD"),
        claim("actual.gross_margin", 18.9, "percent"),
    )
    results = verify_claims(claims, facts)
    assert [r.status for r in results] == [
        Status.VERIFIED,
        Status.FLAGGED,
        Status.VERIFIED,
        Status.UNSUPPORTED,
        Status.FLAGGED,
    ]
    assert results[0].claim is claims[0]
    assert summarize(results) == {
        "verified": 2,
        "flagged": 2,
        "unsupported": 1,
        "total": 5,
    }


def test_summarize_empty_is_all_zero() -> None:
    assert summarize(()) == {"verified": 0, "flagged": 0, "unsupported": 0, "total": 0}


def test_status_values_are_exact() -> None:
    assert [status.value for status in Status] == ["verified", "flagged", "unsupported"]


@pytest.fixture(scope="module")
def sheet() -> tuple[Fact, ...]:
    connection = build_database()
    run_model(connection, publish_forward=False)
    run_variance(connection)
    return quarter_facts(connection, QUARTER)


def test_integration_verifies_a_correct_revenue_claim(sheet: tuple[Fact, ...]) -> None:
    revenue = lookup(sheet)[("actual.total_revenue", QUARTER)]
    billions = float((revenue.value / Decimal(10**9)).quantize(Decimal("0.01")))
    correct = claim("actual.total_revenue", billions, "USD billion")
    result = verify_claims((correct,), sheet)[0]
    assert result.status is Status.VERIFIED
    assert result.expected == revenue.value
    assert result.source == revenue.source
    assert result.source_url == revenue.source_url


def test_integration_flags_a_revenue_claim_off_by_ten_percent(sheet: tuple[Fact, ...]) -> None:
    revenue = lookup(sheet)[("actual.total_revenue", QUARTER)]
    billions = float((revenue.value / Decimal(10**9)).quantize(Decimal("0.01")))
    wrong = claim("actual.total_revenue", round(billions * 1.1, 2), "USD billion")
    result = verify_claims((wrong,), sheet)[0]
    assert result.status is Status.FLAGGED
    assert result.expected == revenue.value


def test_integration_checks_a_signed_variance(sheet: tuple[Fact, ...]) -> None:
    variance = lookup(sheet)[("variance.total_revenue", QUARTER)]
    assert variance.value < 0
    billions = float((variance.value / Decimal(10**9)).quantize(Decimal("0.01")))
    signed = claim("variance.total_revenue", billions, "USD billion")
    unsigned = claim("variance.total_revenue", -billions, "USD billion")
    assert verify_claim(signed, lookup(sheet)).status is Status.VERIFIED
    assert verify_claim(unsigned, lookup(sheet)).status is Status.FLAGGED


def test_integration_unknown_period_is_unsupported(sheet: tuple[Fact, ...]) -> None:
    result = verify_claims((claim("actual.total_revenue", 1, "USD billion", "2030-Q1"),), sheet)[0]
    assert result.status is Status.UNSUPPORTED
