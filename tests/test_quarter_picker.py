"""Acceptance checks for the M5-T2 quarter shell.

The picker behavior runs in the site test command. These tests lock the
required copy and keep wireframe dollar amounts out of the fixture.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SITE_SRC = REPO_ROOT / "site" / "src"

NEEDS_HISTORY = "No forecast for this quarter: it needs four earlier quarters of history."
DISCLAIMER = (
    "Independent analysis built from Tesla's public SEC filings and investor-relations "
    "releases. Not affiliated with or endorsed by Tesla, Inc. Not investment advice."
)


def test_fixture_marks_history_and_names_the_latest_quarter() -> None:
    text = (SITE_SRC / "quarters.ts").read_text(encoding="utf-8")
    assert NEEDS_HISTORY in text
    assert "hasForecast: false" in text
    assert "hasForecast: true" in text
    assert text.index("2025-Q4") < text.index("2026-Q3")
    assert '{ id: "2026-Q3", label: "Q3 2026", hasForecast: true }' in text
    assert "$" not in text
    assert "24.1" not in text


def test_shell_keeps_the_header_disclaimer_and_history_message() -> None:
    app = (SITE_SRC / "App.tsx").read_text(encoding="utf-8")
    config = (SITE_SRC / "config.ts").read_text(encoding="utf-8")
    assert "Tesla FP&A Agent" in config
    assert DISCLAIMER in config
    assert "QuarterPicker" in app
    assert "needsHistoryMessage" in app
    headline = "Tesla's quarter, forecast and explained by an agent, checked against the filings."
    assert headline in app
