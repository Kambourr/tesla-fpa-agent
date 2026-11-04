"""The forecast config loads, and its inputs stay before the target quarter."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from agent.forecast_config import (
    REQUIRED_DRIVERS,
    ForecastConfig,
    load_forecast_config,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_committed_config_loads_and_names_every_required_driver() -> None:
    config = load_forecast_config()
    assert config.cutoff == "previous_quarter_filing_date"
    assert config.minimum_earlier_quarters == 4
    assert config.value_basis == "latest_stored_value_on_cutoff"
    for name in REQUIRED_DRIVERS:
        assert name in config.drivers
    assert set(config.scenarios) == {"deliveries", "automotive_asp", "gross_margin"}


def test_every_driver_input_is_an_earlier_quarter() -> None:
    config = load_forecast_config()
    for name, driver in config.drivers.items():
        assert driver.input_offsets
        assert all(offset < 0 for offset in driver.input_offsets), name


def test_deliveries_use_last_year_and_growth_before_the_cutoff() -> None:
    driver = load_forecast_config().drivers["deliveries"]
    assert driver.method == "same_quarter_last_year_times_recent_yoy"
    assert "D(Q-4)" in driver.formula
    assert "D(Q-1)" in driver.formula
    assert "D(Q-5)" in driver.formula
    assert set(driver.input_offsets) == {-1, -4, -5}


def test_automotive_sales_are_deliveries_times_asp() -> None:
    driver = load_forecast_config().drivers["automotive_sales"]
    assert driver.method == "deliveries_times_asp"
    assert "Forecast deliveries for Q times forecast ASP for Q" in driver.formula


def test_scenario_flexes_are_explicit_and_ordered() -> None:
    scenarios = load_forecast_config().scenarios
    deliveries = scenarios["deliveries"]
    asp = scenarios["automotive_asp"]
    margin = scenarios["gross_margin"]
    assert (deliveries.bull, deliveries.base, deliveries.bear) == (10, 0, -10)
    assert deliveries.unit == "percent"
    assert (asp.bull, asp.base, asp.bear, asp.unit) == (5, 0, -5, "percent")
    assert (margin.bull, margin.base, margin.bear, margin.unit) == (100, 0, -100, "basis_points")
    for flex in scenarios.values():
        assert flex.bull > flex.base > flex.bear


def test_identities_define_revenue_profit_and_cash_flow() -> None:
    identities = load_forecast_config().identities
    assert "Automotive sales" in identities["total_revenue"]
    assert "capex" in identities["free_cash_flow"]
    assert "operating expenses" in identities["operating_income"]


def test_a_same_quarter_input_is_rejected() -> None:
    payload = json.loads((REPO_ROOT / "config" / "forecast.json").read_text(encoding="utf-8"))
    payload["drivers"]["deliveries"]["input_offsets"] = [-4, 0]
    with pytest.raises(ValidationError, match="look-ahead"):
        ForecastConfig.model_validate(payload)


def test_a_reversed_scenario_is_rejected() -> None:
    payload = json.loads((REPO_ROOT / "config" / "forecast.json").read_text(encoding="utf-8"))
    payload["scenarios"]["deliveries"]["bear"] = 15
    with pytest.raises(ValidationError, match="bull must be above base"):
        ForecastConfig.model_validate(payload)
