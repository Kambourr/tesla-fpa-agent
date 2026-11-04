"""Load the documented forecast formulas.

The config describes the base forecast and the bull, base, and bear flexes.
It does not compute a forecast. Every driver input is an earlier quarter.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "config" / "forecast.json"

REQUIRED_DRIVERS = (
    "deliveries",
    "automotive_asp",
    "automotive_sales",
    "regulatory_credits",
    "energy",
    "services",
    "gross_margin",
    "operating_expenses",
    "capex",
)

SCENARIO_UNITS = {
    "deliveries": "percent",
    "automotive_asp": "percent",
    "gross_margin": "basis_points",
}


class DriverSpec(BaseModel):
    """How one line is projected from quarters before the target."""

    model_config = ConfigDict(extra="forbid")

    method: str = Field(min_length=1)
    formula: str = Field(min_length=1)
    input_offsets: list[int] = Field(min_length=1)
    notes: str = Field(min_length=1)

    @field_validator("input_offsets")
    @classmethod
    def inputs_are_earlier_quarters(cls, offsets: list[int]) -> list[int]:
        if any(offset >= 0 for offset in offsets):
            raise ValueError(f"look-ahead offset in {offsets}")
        return offsets


class ScenarioFlex(BaseModel):
    """Bull, base, and bear flex for one driver. Base is unflexed."""

    model_config = ConfigDict(extra="forbid")

    bull: int
    base: int
    bear: int
    unit: Literal["percent", "basis_points"]

    @model_validator(mode="after")
    def bull_above_base_above_bear(self) -> Self:
        if not self.bull > self.base > self.bear:
            raise ValueError("bull must be above base and bear below base")
        if self.base != 0:
            raise ValueError("base flex must be zero")
        return self


class ForecastConfig(BaseModel):
    """The forecast rules M2-T3 will execute."""

    model_config = ConfigDict(extra="forbid")

    cutoff: Literal["previous_quarter_filing_date"]
    minimum_earlier_quarters: Literal[4]
    value_basis: Literal["latest_stored_value_on_cutoff"]
    drivers: dict[str, DriverSpec]
    identities: dict[str, str]
    scenarios: dict[str, ScenarioFlex]

    @model_validator(mode="after")
    def covers_the_drivers_and_flexes(self) -> Self:
        missing = [name for name in REQUIRED_DRIVERS if name not in self.drivers]
        if missing:
            raise ValueError(f"missing drivers: {', '.join(missing)}")
        if set(self.scenarios) != set(SCENARIO_UNITS):
            raise ValueError("scenarios must be deliveries, automotive ASP, and gross margin")
        for name, unit in SCENARIO_UNITS.items():
            if self.scenarios[name].unit != unit:
                raise ValueError(f"{name} flex unit must be {unit}")
        for name in ("total_revenue", "gross_profit", "operating_income", "free_cash_flow"):
            if name not in self.identities or not self.identities[name].strip():
                raise ValueError(f"missing identity: {name}")
        return self


def load_forecast_config(path: Path | None = None) -> ForecastConfig:
    """Read the forecast config. Does not fetch filings or deliveries."""
    source = DEFAULT_PATH if path is None else path
    payload = json.loads(source.read_text(encoding="utf-8"))
    return ForecastConfig.model_validate(payload)
