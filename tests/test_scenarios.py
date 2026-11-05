"""Bull and bear flex the configured drivers. Base matches the unflexed forecast."""

from decimal import Decimal

from tests.test_forecast import TARGET, _history

from agent.forecast import write_base_forecast
from agent.forecast_config import ForecastConfig, load_forecast_config
from agent.forecast_inputs import load_forecast_inputs
from agent.scenarios import scenario_forecasts, write_scenarios


def _table(connection, scenario: str) -> dict[str, Decimal | None]:
    rows = connection.execute(
        "SELECT metric, value FROM forecast WHERE quarter = ? AND scenario = ?",
        [TARGET, scenario],
    ).fetchall()
    return {metric: None if value is None else Decimal(value) for metric, value in rows}


def test_base_scenario_matches_the_unflexed_forecast() -> None:
    connection = _history()
    write_base_forecast(connection, TARGET)
    base = _table(connection, "base")
    write_scenarios(connection, TARGET)
    assert _table(connection, "base") == base
    config = load_forecast_config()
    bull = _table(connection, "bull")
    bear = _table(connection, "bear")
    bull_deliveries = base["deliveries"] * (1 + Decimal(config.scenarios["deliveries"].bull) / 100)
    bear_deliveries = base["deliveries"] * (1 + Decimal(config.scenarios["deliveries"].bear) / 100)
    assert bull["deliveries"] == bull_deliveries.quantize(Decimal("0.0001"))
    assert bear["deliveries"] == bear_deliveries.quantize(Decimal("0.0001"))
    assert bull["deliveries"] > base["deliveries"] > bear["deliveries"]
    assert bull["automotive_asp"] > base["automotive_asp"] > bear["automotive_asp"]
    assert bull["gross_margin"] > base["gross_margin"] > bear["gross_margin"]
    assert bull["automotive_regulatory_credits"] == base["automotive_regulatory_credits"]
    assert bear["free_cash_flow"] == base["free_cash_flow"]
    bull_asp = base["automotive_asp"] * (1 + Decimal(config.scenarios["automotive_asp"].bull) / 100)
    expected_sales = bull["deliveries"] * bull_asp.quantize(Decimal("0.0001"))
    assert bull["automotive_sales"] == expected_sales.quantize(Decimal("0.0001"))


def test_scenario_percentages_come_from_the_passed_config() -> None:
    connection = _history()
    write_scenarios(connection, TARGET)
    base = _table(connection, "base")
    payload = load_forecast_config().model_dump()
    payload["scenarios"]["deliveries"]["bull"] = 20
    tweaked = ForecastConfig.model_validate(payload)
    scenarios = scenario_forecasts(load_forecast_inputs(connection, TARGET), tweaked)
    bull = {line.metric: line.value for line in scenarios["bull"]}
    expected = (base["deliveries"] * Decimal("1.20")).quantize(Decimal("0.0001"))
    assert bull["deliveries"] == expected
