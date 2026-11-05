"""M5-T9: the committed scenario parity fixture is what the Python model produces now."""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "make_scenario_fixture.py"
COMMITTED = REPO_ROOT / "site" / "src" / "data" / "scenarioParity.fixture.json"
FOUR_PLACES = re.compile(r"^-?\d+\.\d{4}$")


def _script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("make_scenario_fixture", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_fixture_matches_the_python_model() -> None:
    script = _script()
    regenerated = script.render(script.build_fixture())
    assert COMMITTED.read_text(encoding="utf-8") == regenerated, (
        "scenarioParity.fixture.json is stale: rerun uv run python scripts/make_scenario_fixture.py"
    )


def test_fixture_shape_and_four_decimal_strings() -> None:
    fixture = json.loads(COMMITTED.read_text(encoding="utf-8"))
    assert fixture["generated_by"] == "scripts/make_scenario_fixture.py"
    assert len(fixture["cases"]) == 4
    for case in fixture["cases"]:
        assert set(case["expected"]) == {"bull", "bear"}
        for text in [
            *case["drivers"].values(),
            *(value for scenario in case["expected"].values() for value in scenario.values()),
        ]:
            if text is not None:
                assert FOUR_PLACES.match(text), text
