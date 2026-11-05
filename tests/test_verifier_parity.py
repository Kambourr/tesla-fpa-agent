"""The site's TypeScript verifier must agree with agent/verifier.py.

The cases are built from fixed inputs and written to
site/src/verify/parity.json with the Python verifier's status for each. The
site's vitest suite runs the same cases through site/src/verify/verifier.ts.
This test fails when the committed file is out of date; regenerate it with
``uv run python tests/test_verifier_parity.py``.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from agent.fact_sheet import Fact, lookup
from agent.narrative import Claim
from agent.verifier import verify_claim

PARITY_PATH = Path(__file__).resolve().parents[1] / "site" / "src" / "verify" / "parity.json"

# (expected value, fact unit, written value, written unit)
_BASES: list[tuple[str, str, float, str]] = [
    ("28046000000", "USD", 28.05, "USD billion"),
    ("-7481465181.4722", "USD", -7.48, "USD billion"),
    ("720000000", "USD", 720.0, "USD million"),
    ("23500000", "USD", 23.5, "USD million"),
    ("0", "USD", 0.0, "USD million"),
    ("19.6", "percent", 19.6, "percent"),
    ("-21.1", "percent", -21.1, "percent"),
    ("0.9", "percent", 0.9, "percentage points"),
    ("134835", "units", 134.8, "thousand units"),
    ("497099", "units", 497.1, "thousand vehicles"),
    ("462890", "units", 462890.0, "vehicles"),
    ("41250.5", "USD_per_unit", 41250.5, "USD per unit"),
]
_FACTORS = [1.0, 1.004, 0.996, 1.006, 0.994, 1.05, -1.0, 10.0, 0.001]
_UNIT_SWAPS = {
    "USD billion": "USD million",
    "USD million": "USD billion",
    "percent": "USD",
    "percentage points": "percent",
    "thousand units": "units",
    "thousand vehicles": "vehicles",
    "vehicles": "thousand vehicles",
    "USD per unit": "USD",
}


def build_cases() -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []
    written_variants: list[tuple[str, str, float, str]] = []
    for expected, fact_unit, written, unit in _BASES:
        for factor in _FACTORS:
            written_variants.append((expected, fact_unit, round(written * factor, 6), unit))
        written_variants.append((expected, fact_unit, written, _UNIT_SWAPS[unit]))
    for expected, fact_unit, delta in [("19.6", "percent", 0.1), ("19.6", "percent", 0.11)]:
        written_variants.append((expected, fact_unit, round(19.6 + delta, 6), "percent"))
    written_variants += [
        ("134835", "units", 134.84, "thousand units"),
        ("134835", "units", 135.0, "thousand units"),
        ("134850", "units", 134.9, "thousand units"),
        ("134849", "units", 134.8, "thousand units"),
    ]
    for expected, fact_unit, written, unit in written_variants:
        fact = Fact(key="k", period="p", value=Decimal(expected), unit=fact_unit, source="s")
        claim = Claim(metric="k", period="p", value=written, unit=unit, sentence_ref="1")
        result = verify_claim(claim, lookup((fact,)))
        cases.append(
            {
                "expected": float(Decimal(expected)),
                "expected_unit": fact_unit,
                "value": written,
                "value_text": str(Decimal(str(written))),
                "unit": unit,
                "status": result.status.value,
            }
        )
    return cases


def _text() -> str:
    return json.dumps(build_cases(), indent=1) + "\n"


def test_parity_file_matches_the_python_verifier() -> None:
    assert PARITY_PATH.read_text(encoding="utf-8") == _text()


def test_cases_cover_every_status() -> None:
    statuses = {case["status"] for case in build_cases()}
    assert statuses == {"verified", "flagged"}


if __name__ == "__main__":
    PARITY_PATH.write_text(_text(), encoding="utf-8")
    print(f"wrote {PARITY_PATH}")
