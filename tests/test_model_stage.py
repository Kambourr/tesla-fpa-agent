"""`python -m agent model` and `variance` on a fixture database."""

from __future__ import annotations

import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest

from agent.deliveries import repo_root
from agent.model_stage import StageError, run_model, run_variance
from pipeline_fixture import build_database

PUBLISHED = (
    "2023-Q4",
    "2024-Q1",
    "2024-Q2",
    "2024-Q3",
    "2024-Q4",
    "2025-Q1",
    "2025-Q2",
    "2025-Q3",
    "2025-Q4",
    "2026-Q1",
    "2026-Q2",
    "2026-Q3",
)


def test_model_writes_twelve_quarters_and_no_forward_quarter() -> None:
    connection = build_database()
    result = run_model(connection, publish_forward=False)
    assert result.quarters == PUBLISHED
    assert result.without_forecast == ()
    assert result.forward_quarter is None
    published = connection.execute(
        "SELECT quarter, kind, has_forecast FROM published_quarter ORDER BY quarter"
    ).fetchall()
    assert published == [(quarter, "backtest", True) for quarter in PUBLISHED]
    scenarios = connection.execute(
        "SELECT quarter, count(DISTINCT scenario) FROM forecast GROUP BY quarter ORDER BY quarter"
    ).fetchall()
    assert scenarios == [(quarter, 3) for quarter in PUBLISHED]
    assert connection.execute("SELECT count(*) FROM backtest").fetchone() == (36,)
    forward = connection.execute("SELECT count(*) FROM forecast WHERE quarter = '2026-Q4'")
    assert forward.fetchone() == (0,)


def test_forward_quarter_only_with_the_flag() -> None:
    connection = build_database()
    result = run_model(connection, publish_forward=True)
    assert result.forward_quarter == "2026-Q4"
    kinds = connection.execute(
        "SELECT kind, count(*) FROM published_quarter GROUP BY kind ORDER BY kind"
    ).fetchall()
    assert kinds == [("backtest", 12), ("forward", 1)]
    rows = connection.execute(
        "SELECT count(*) FROM forecast WHERE quarter = '2026-Q4' AND value IS NOT NULL"
    ).fetchone()
    assert rows is not None and rows[0] > 0
    # Turning the flag back off removes the forward quarter on the next run.
    run_model(connection, publish_forward=False)
    assert connection.execute(
        "SELECT count(*) FROM forecast WHERE quarter = '2026-Q4'"
    ).fetchone() == (0,)


def _variance(connection: duckdb.DuckDBPyConnection, quarter: str, bridge: str) -> Decimal:
    def actual(metric: str) -> Decimal:
        found = connection.execute(
            "SELECT value FROM quarter_actual WHERE quarter = ? AND metric = ?",
            [quarter, metric],
        ).fetchone()
        assert found is not None
        return found[0]

    def forecast(metric: str) -> Decimal:
        found = connection.execute(
            "SELECT value FROM forecast WHERE quarter = ? AND metric = ? AND scenario = 'base'",
            [quarter, metric],
        ).fetchone()
        assert found is not None
        return found[0]

    if bridge == "free_cash_flow":
        cfo, capex = "net_cash_from_operating_activities", "purchases_of_property_and_equipment"
        return actual(cfo) - actual(capex) - forecast("free_cash_flow")
    metric = "total_revenue" if bridge == "revenue" else bridge
    return actual(metric) - forecast(metric)


def test_variance_writes_four_exact_bridges_per_quarter() -> None:
    connection = build_database()
    run_model(connection, publish_forward=False)
    result = run_variance(connection)
    assert result.failures == ()
    assert result.written == 48
    sums = connection.execute(
        "SELECT quarter, bridge, sum(value), count(*) FROM bridge GROUP BY quarter, bridge"
    ).fetchall()
    assert len(sums) == 48
    for quarter, bridge, total, _count in sums:
        assert total == _variance(connection, quarter, bridge), (quarter, bridge)
    restructuring = connection.execute(
        """
        SELECT value FROM bridge
        WHERE quarter = '2025-Q4' AND bridge = 'operating_income'
          AND driver = 'restructuring_and_other'
        """
    ).fetchone()
    assert restructuring is not None and restructuring[0] < 0


def test_variance_reports_a_bridge_it_cannot_build() -> None:
    connection = build_database()
    run_model(connection, publish_forward=False)
    connection.execute(
        "DELETE FROM quarter_actual WHERE quarter = '2026-Q3' AND metric = 'automotive_leasing'"
    )
    result = run_variance(connection)
    assert result.written == 46
    assert any(item.startswith("2026-Q3 revenue:") for item in result.failures)
    assert any(item.startswith("2026-Q3 gross_profit:") for item in result.failures)


def test_stages_need_their_inputs() -> None:
    connection = duckdb.connect()
    from agent.schema import apply_schema

    apply_schema(connection)
    with pytest.raises(StageError, match="ingest"):
        run_model(connection, publish_forward=False)
    with pytest.raises(StageError, match="model"):
        run_variance(connection)


def test_cli_runs_both_stages_without_printing_secrets(tmp_path: Path) -> None:
    database = tmp_path / "fpa.duckdb"
    build_database(str(database)).close()
    environment = dict(os.environ)
    environment.update(
        OPENAI_API_KEY="sk-test-not-a-real-key",
        SEC_USER_AGENT="fixture-contact-string",
        PUBLISH_FORWARD_FORECAST="false",
        PYTHONPATH=str(repo_root()),
    )
    outputs = []
    for command in ("model", "variance"):
        completed = subprocess.run(
            [sys.executable, "-m", "agent", command, "--database", str(database)],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            env=environment,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        outputs.append(completed.stdout + completed.stderr)
    joined = "\n".join(outputs)
    assert "model wrote forecasts for 12 quarters, 2023-Q4 to 2026-Q3" in joined
    assert "forward forecast is off" in joined
    assert "variance wrote 48 bridges" in joined
    assert "sk-test-not-a-real-key" not in joined
    assert "fixture-contact-string" not in joined


def test_cli_fails_without_a_database(tmp_path: Path) -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "agent", "model", "--database", str(tmp_path / "none.duckdb")],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(repo_root())},
        check=False,
    )
    assert completed.returncode == 1
    assert "Run `python -m agent ingest` first" in completed.stderr
