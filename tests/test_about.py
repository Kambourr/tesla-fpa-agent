"""Acceptance checks for the about section profile links."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SITE_SRC = REPO_ROOT / "site" / "src"

CREDIT = "Built by Jacob Kambour, MS Finance & Analytics, Santa Clara University."
GITHUB = "https://github.com/Kambourr"
LINKEDIN = "https://www.linkedin.com/in/jacob-kambour-5558a2221/"


def test_about_uses_the_credit_and_public_profile_links() -> None:
    about = (SITE_SRC / "components" / "AboutSection.tsx").read_text(encoding="utf-8")
    config = (SITE_SRC / "config.ts").read_text(encoding="utf-8")
    app = (SITE_SRC / "App.tsx").read_text(encoding="utf-8")
    assert CREDIT in about
    assert "profileLinks" in about
    assert "AboutSection" in app
    assert f'github: "{GITHUB}"' in config
    assert f'linkedin: "{LINKEDIN}"' in config
    assert "resume" not in config
    assert "Résumé" not in about
    assert "resume" not in about.lower()
    assert "mailto:" not in config.lower()
    assert "mailto:" not in about.lower()
    assert GITHUB in about or "profileLinks.github" in about
    assert LINKEDIN in about or "profileLinks.linkedin" in about
