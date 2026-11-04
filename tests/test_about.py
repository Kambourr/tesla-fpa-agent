"""Acceptance checks for the M5-T14 about section."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SITE_SRC = REPO_ROOT / "site" / "src"

CREDIT = "Built by Jacob Kambour, MS Finance & Analytics, Santa Clara University."


def test_about_uses_the_credit_and_blank_profile_links() -> None:
    about = (SITE_SRC / "components" / "AboutSection.tsx").read_text(encoding="utf-8")
    config = (SITE_SRC / "config.ts").read_text(encoding="utf-8")
    app = (SITE_SRC / "App.tsx").read_text(encoding="utf-8")
    assert CREDIT in about
    assert "profileLinks" in about
    assert "Not filled in yet" in about
    assert "AboutSection" in app
    assert 'github: ""' in config
    assert 'linkedin: ""' in config
    assert 'resume: ""' in config
    assert "http://" not in config
    assert "https://" not in config
    assert "http://" not in about
    assert "https://" not in about
