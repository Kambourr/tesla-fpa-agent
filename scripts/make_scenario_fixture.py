"""Write the shared scenario parity fixture for the browser test (M5-T9).

Builds the synthetic pipeline database, runs the model, and reads the published
drivers for the four latest quarters with a base forecast. Each driver is four
decimals, as agent/publish.py writes it. Python runs ``agent.scenarios._flex``
on base lines built from those exact driver values, and the bull and bear
results are written as four-decimal strings to
``site/src/data/scenarioParity.fixture.json``. The TypeScript test recomputes
the same cases with ``recomputeScenario`` and must match.

The numbers come from an invented database. They are not Tesla data.

Usage: uv run python scripts/make_scenario_fixture.py
"""

from __future__ import annotations

import json
import sys
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "site" / "src" / "data" / "scenarioParity.fixture.json"
CASE_COUNT = 4
PLACES = Decimal("0.0001")
SCENARIOS = ("bull", "bear")
DRIVER_KEYS = (
    "deliveries",
    "automotive_asp",
    "gross_margin",
    "automotive_regulatory_credits",
    "automotive_leasing",
    "energy_generation_and_storage",
    "services_and_other",
    "operating_expenses",
)
OUTPUT_KEYS = (
    "deliveries",
    "automotive_asp",
    "automotive_sales",
    "total_revenue",
    "gross_margin",
    "gross_profit",
    "operating_income",
)
# Config scenario name to the ScenarioFlex key in site/src/data/types.ts.
FLEX_KEYS = {
    "deliveries": ("deliveries_pct", "percent"),
    "automotive_asp": ("automotive_asp_pct", "percent"),
    "gross_margin": ("gross_margin_bp", "basis_points"),
}


def _four(value: float | None) -> str | None:
    """A published driver as its exact four-decimal string. Raises if it has more places."""
    if value is None:
        return None
    exact = Decimal(repr(value))
    rounded = exact.quantize(PLACES, rounding=ROUND_HALF_EVEN)
    if rounded != exact:
        raise ValueError(f"driver {value!r} does not have four decimal places")
    return format(rounded, "f")


def _output(value: Decimal | None) -> str | None:
    """A Python scenario result as its four-decimal string. _flex already quantizes it."""
    if value is None:
        return None
    if value.quantize(PLACES, rounding=ROUND_HALF_EVEN) != value:
        raise ValueError(f"scenario value {value} does not have four decimal places")
    return format(value, "f")


def build_fixture() -> dict[str, Any]:
    """Compute the fixture in memory. Deterministic: rerunning gives the same dict."""
    tests_dir = str(REPO_ROOT / "tests")
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)

    from agent.forecast import ForecastLine
    from agent.forecast_config import load_forecast_config
    from agent.model_stage import run_model
    from agent.publish import build_dashboard
    from agent.scenarios import _flex
    from pipeline_fixture import build_database

    config = load_forecast_config()
    connection = build_database()
    run_model(connection, publish_forward=False)
    dashboard = build_dashboard(connection)

    ready = sorted(
        (view for view in dashboard.quarters if view.has_forecast),
        key=lambda view: view.quarter,
    )
    if len(ready) < CASE_COUNT:
        raise RuntimeError(f"need {CASE_COUNT} quarters with a forecast, found {len(ready)}")

    cases = []
    for view in ready[-CASE_COUNT:]:
        if view.drivers is None:
            raise RuntimeError(f"{view.quarter} has a forecast but no drivers")
        drivers = {key: _four(getattr(view.drivers, key)) for key in DRIVER_KEYS}
        missing = [key for key, text in drivers.items() if text is None]
        if missing:
            raise RuntimeError(f"{view.quarter} has null drivers: {', '.join(missing)}")
        base = tuple(
            ForecastLine(metric=key, value=Decimal(text), empty_history=False)
            for key, text in drivers.items()
            if text is not None
        )
        expected: dict[str, dict[str, str | None]] = {}
        for scenario in SCENARIOS:
            values = {line.metric: line.value for line in _flex(base, config, scenario)}
            expected[scenario] = {key: _output(values.get(key)) for key in OUTPUT_KEYS}
        cases.append({"quarter": view.quarter, "drivers": drivers, "expected": expected})

    flex: dict[str, dict[str, int]] = {}
    for name, (key, unit) in FLEX_KEYS.items():
        scenario_flex = config.scenarios[name]
        if scenario_flex.unit != unit:
            raise RuntimeError(f"{name} unit is {scenario_flex.unit}, expected {unit}")
        flex[key] = {
            "bull": scenario_flex.bull,
            "base": scenario_flex.base,
            "bear": scenario_flex.bear,
        }

    return {
        "generated_by": "scripts/make_scenario_fixture.py",
        "note": "synthetic numbers for a parity test, not Tesla data",
        "flex": flex,
        "cases": cases,
    }


def render(fixture: dict[str, Any]) -> str:
    """The exact text written to the fixture file."""
    return json.dumps(fixture, indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    FIXTURE_PATH.write_text(render(build_fixture()), encoding="utf-8")
    print(f"wrote {FIXTURE_PATH}")


if __name__ == "__main__":
    main()
