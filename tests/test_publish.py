"""The dashboard JSON: schema lock, fixture contents, forward quarter, and the CLI."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest

from agent.deliveries import repo_root
from agent.model_stage import run_model, run_variance
from agent.publish import PublishError, build_dashboard, write_dashboard
from agent.publish_schema import Dashboard, schema_text
from pipeline_fixture import build_database

REPO_ROOT = repo_root()
SCHEMA_PATH = REPO_ROOT / "site" / "src" / "data" / "dashboard.schema.json"
FAKE_OPENAI_KEY = "fake-openai-value-for-test"
FAKE_SEC_AGENT = "fake-contact-for-test@example.com"

# Written out here, not imported, so a change to the module constant must match the spec.
EXPECTED_LINE_ORDER = [
    "deliveries",
    "automotive_asp",
    "automotive_sales",
    "automotive_regulatory_credits",
    "automotive_leasing",
    "energy_generation_and_storage",
    "services_and_other",
    "total_revenue",
    "gross_profit",
    "gross_margin",
    "research_and_development",
    "selling_general_and_administrative",
    "operating_expenses",
    "operating_income",
    "net_cash_from_operating_activities",
    "purchases_of_property_and_equipment",
    "free_cash_flow",
]
COST_METRICS = {
    "research_and_development",
    "selling_general_and_administrative",
    "operating_expenses",
    "purchases_of_property_and_equipment",
}


def _fixture(publish_forward: bool = False) -> duckdb.DuckDBPyConnection:
    connection = build_database()
    run_model(connection, publish_forward=publish_forward)
    run_variance(connection)
    return connection


def _amount(connection: duckdb.DuckDBPyConnection, query: str, parameters: list[str]) -> Decimal:
    found = connection.execute(query, parameters).fetchone()
    assert found is not None and found[0] is not None
    return Decimal(found[0])


def test_committed_schema_matches_the_models() -> None:
    assert SCHEMA_PATH.read_text(encoding="utf-8") == schema_text()


def test_fixture_dashboard_validates_and_has_twelve_quarters() -> None:
    dashboard = build_dashboard(_fixture(), now=datetime(2026, 11, 5, 8, tzinfo=UTC))
    assert Dashboard.model_validate_json(dashboard.model_dump_json()) == dashboard
    assert len(dashboard.quarters) == 12
    assert [item.kind for item in dashboard.quarters] == ["backtest"] * 12
    assert dashboard.latest_quarter == "2026-Q3"
    assert dashboard.forward_forecast_published is False
    assert dashboard.generated_at == "2026-11-05T08:00:00+00:00"
    assert dashboard.qa is None
    assert all(item.memo is None for item in dashboard.quarters)


def test_revenue_bridge_sums_to_actual_minus_forecast_total_revenue() -> None:
    connection = _fixture()
    dashboard = build_dashboard(connection)
    for item in dashboard.quarters:
        actual = _amount(
            connection,
            "SELECT value FROM quarter_actual WHERE quarter = ? AND metric = 'total_revenue'",
            [item.quarter],
        )
        forecast = _amount(
            connection,
            "SELECT value FROM forecast WHERE quarter = ? AND metric = 'total_revenue' "
            "AND scenario = 'base'",
            [item.quarter],
        )
        bars = sum(bar.value for bar in item.bridges["revenue"])
        assert abs(bars - float(actual - forecast)) <= 0.0001, item.quarter


def test_lines_are_in_the_specified_order() -> None:
    dashboard = build_dashboard(_fixture())
    for item in dashboard.quarters:
        assert [line.metric for line in item.lines] == EXPECTED_LINE_ORDER, item.quarter


def test_favorable_flags_follow_the_cost_rule() -> None:
    dashboard = build_dashboard(_fixture())
    seen = set()
    for item in dashboard.quarters:
        for line in item.lines:
            if line.variance is None or line.variance == 0:
                assert line.favorable is None, (item.quarter, line.metric)
                continue
            expected = line.variance < 0 if line.metric in COST_METRICS else line.variance > 0
            assert line.favorable is expected, (item.quarter, line.metric)
            seen.add(line.favorable)
        for bridge in item.bridges.values():
            for bar in bridge:
                assert bar.favorable is (bar.value > 0), (item.quarter, bar.driver)
    assert seen == {True, False}


def test_forward_quarter_appears_only_when_published() -> None:
    dashboard = build_dashboard(_fixture(publish_forward=True))
    assert len(dashboard.quarters) == 13
    forward = dashboard.quarters[-1]
    assert forward.quarter == "2026-Q4"
    assert forward.kind == "forward"
    assert forward.label == "Q4 2026"
    assert forward.has_forecast is True
    assert forward.filing is None
    assert dashboard.forward_forecast_published is True
    assert dashboard.latest_quarter == "2026-Q3"
    assert all(line.actual is None for line in forward.lines)
    assert all(not bridge for bridge in forward.bridges.values())


def test_no_forward_quarter_without_the_flag() -> None:
    dashboard = build_dashboard(_fixture(publish_forward=False))
    assert all(item.kind == "backtest" for item in dashboard.quarters)
    assert dashboard.forward_forecast_published is False


def test_empty_published_quarter_is_a_clear_error() -> None:
    connection = build_database()
    with pytest.raises(PublishError, match="python -m agent model"):
        build_dashboard(connection)


def test_written_json_round_trips_and_leaks_no_secrets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", FAKE_OPENAI_KEY)
    monkeypatch.setenv("SEC_USER_AGENT", FAKE_SEC_AGENT)
    dashboard = build_dashboard(_fixture(publish_forward=True))
    path = tmp_path / "dashboard.json"
    write_dashboard(dashboard, path)
    text = path.read_text(encoding="utf-8")
    assert Dashboard.model_validate_json(text) == dashboard
    assert text.endswith("}\n")
    assert text == json.dumps(json.loads(text), indent=2, sort_keys=True) + "\n"
    assert FAKE_OPENAI_KEY not in text
    assert FAKE_SEC_AGENT not in text
    assert "sk-" not in text


def test_cli_writes_the_file(tmp_path: Path) -> None:
    database = tmp_path / "fpa.duckdb"
    connection = build_database(str(database))
    run_model(connection, publish_forward=False)
    run_variance(connection)
    connection.close()
    output = tmp_path / "out" / "dashboard.json"
    result = _run_cli(tmp_path, "publish", "--database", str(database), "--output", str(output))
    assert result.returncode == 0, result.stderr
    assert "publish wrote" in result.stdout
    assert "12 quarters" in result.stdout
    assert FAKE_SEC_AGENT not in result.stdout + result.stderr
    dashboard = Dashboard.model_validate_json(output.read_text(encoding="utf-8"))
    assert dashboard.latest_quarter == "2026-Q3"
    assert dashboard.run.stages[-1].name == "publish"


def test_cli_fails_clearly_when_nothing_is_published(tmp_path: Path) -> None:
    database = tmp_path / "fpa.duckdb"
    build_database(str(database)).close()
    output = tmp_path / "dashboard.json"
    result = _run_cli(tmp_path, "publish", "--database", str(database), "--output", str(output))
    assert result.returncode == 1
    assert "published_quarter is empty" in result.stderr
    assert not output.exists()


def _run_cli(cwd: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = {
        **os.environ,
        "PYTHONPATH": str(REPO_ROOT),
        "OPENAI_API_KEY": FAKE_OPENAI_KEY,
        "SEC_USER_AGENT": FAKE_SEC_AGENT,
    }
    return subprocess.run(
        [sys.executable, "-m", "agent", *arguments],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
