"""Acceptance checks for the M5-T13 methods section."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SITE_SRC = REPO_ROOT / "site" / "src"

EXAMPLE_NOTE = "Example of the pipeline. Not a recorded run."
STAGES = ("Ingest", "Load", "Forecast", "Explain", "Verify", "Publish")


def test_example_diagram_names_the_six_stages_and_who_does_them() -> None:
    fixture = (SITE_SRC / "methodExample.ts").read_text(encoding="utf-8")
    section = (SITE_SRC / "components" / "MethodSection.tsx").read_text(encoding="utf-8")
    assert EXAMPLE_NOTE in fixture
    assert "Not a recorded run" in fixture
    assert "$" not in fixture
    for name in STAGES:
        assert name in fixture
    assert 'actor: "Model"' in fixture
    assert "<svg" in section
    assert "methodExample" in section


def test_methods_copy_covers_the_controls_and_the_leasing_limit() -> None:
    section = (SITE_SRC / "components" / "MethodSection.tsx").read_text(encoding="utf-8")
    app = (SITE_SRC / "App.tsx").read_text(encoding="utf-8")
    assert "MethodSection" in app
    assert "This page does not call the model." in section
    assert "verified, flagged, or unsupported" in section
    assert "public SEC filings" in section
    assert "investor-relations" in section
    assert "Leased units are counted in total deliveries." in section
    assert "No other feed is used." in section
    assert "→" not in section
    assert "logo" not in section.lower()
