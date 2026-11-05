"""Acceptance checks for the site shell.

The build command itself runs in CI. These tests lock the Pages base path,
the M7 redesign palette (which replaced the brief's section 6 palette; see
docs/DECISIONS.md), both typefaces, tabular figures, and the dark theme.
"""

import re
import struct
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SITE = REPO_ROOT / "site"

LIGHT_PAPER = "#F2F4EF"
LIGHT_INK = "#1D2321"
LIGHT_SURFACE = "#FBFCFA"
LIGHT_ACCENTS = ("#4F5B55", "#3B5878", "#17784C", "#9A5707")
LIGHT_HEXES = (LIGHT_PAPER, LIGHT_INK, "#C7CDC4", *LIGHT_ACCENTS, LIGHT_SURFACE)
DARK_PAPER = "#141A18"
DARK_INK = "#E3E8E4"
DARK_SURFACE = "#1C2421"
DARK_COBALT = "#93ACCB"
DARK_GREEN = "#4CC08A"
DARK_AMBER = "#E9A04A"

FORBIDDEN_HEXES = (
    "#E31937",
    "#CC0000",
    "#E82127",
    "#C8102E",
    "#FF0000",
    "#E3192D",
)

SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"x-access-token:[A-Za-z0-9._\-]+"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
)


def _channel(value: int) -> float:
    channel = value / 255
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def _luminance(hex_color: str) -> float:
    red = int(hex_color[1:3], 16)
    green = int(hex_color[3:5], 16)
    blue = int(hex_color[5:7], 16)
    return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)


def _contrast(foreground: str, background: str) -> float:
    lighter = max(_luminance(foreground), _luminance(background))
    darker = min(_luminance(foreground), _luminance(background))
    return (lighter + 0.05) / (darker + 0.05)


def _git_check_ignore(path: str) -> int:
    result = subprocess.run(
        ["git", "check-ignore", "-q", path],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode


def test_pages_base_path_is_the_repo_name() -> None:
    text = (SITE / "vite.config.ts").read_text(encoding="utf-8")
    assert 'base: "/tesla-fpa-agent/"' in text


def test_package_json_builds_with_npm_and_the_lockfile_is_tracked() -> None:
    package = (SITE / "package.json").read_text(encoding="utf-8")
    assert '"build": "tsc -b && vite build"' in package
    assert (SITE / "package-lock.json").is_file()
    assert _git_check_ignore("site/package-lock.json") == 1
    assert _git_check_ignore("site/node_modules/vite/package.json") == 0
    assert _git_check_ignore("site/dist/index.html") == 0


def test_light_palette_matches_the_redesign() -> None:
    text = (SITE / "src" / "styles" / "tokens.css").read_text(encoding="utf-8")
    for hex_color in LIGHT_HEXES:
        assert hex_color in text
    for forbidden in FORBIDDEN_HEXES:
        assert forbidden.lower() not in text.lower()


def test_dark_palette_keeps_the_same_hues_and_meets_aa() -> None:
    text = (SITE / "src" / "styles" / "tokens.css").read_text(encoding="utf-8")
    for hex_color in (DARK_PAPER, DARK_INK, DARK_SURFACE, DARK_COBALT, DARK_GREEN, DARK_AMBER):
        assert hex_color in text

    assert _contrast(DARK_INK, DARK_PAPER) >= 4.5
    assert _contrast(DARK_INK, DARK_SURFACE) >= 4.5
    for accent in (DARK_COBALT, DARK_GREEN, DARK_AMBER):
        assert _contrast(accent, DARK_PAPER) >= 4.5
        assert _contrast(accent, DARK_SURFACE) >= 4.5

    assert _contrast(LIGHT_INK, LIGHT_PAPER) >= 4.5
    assert _contrast(LIGHT_INK, LIGHT_SURFACE) >= 4.5
    for accent in LIGHT_ACCENTS:
        assert _contrast(accent, LIGHT_PAPER) >= 4.5
        assert _contrast(accent, LIGHT_SURFACE) >= 4.5


def test_type_uses_the_redesign_faces_and_tabular_figures() -> None:
    tokens = (SITE / "src" / "styles" / "tokens.css").read_text(encoding="utf-8")
    global_css = (SITE / "src" / "styles" / "global.css").read_text(encoding="utf-8")
    main = (SITE / "src" / "main.tsx").read_text(encoding="utf-8")
    assert "Schibsted Grotesk" in tokens
    assert "Newsreader" in tokens
    assert "@fontsource/schibsted-grotesk/" in main
    assert "@fontsource/newsreader/" in main
    assert "font-variant-numeric: tabular-nums" in global_css
    assert "line-height: 1.55" in global_css
    assert "1120px" in tokens
    assert "680px" in tokens
    assert "prefers-reduced-motion" in global_css


def test_shell_copy_has_no_hype_emoji_or_brand_red() -> None:
    app = (SITE / "src" / "App.tsx").read_text(encoding="utf-8")
    config = (SITE / "src" / "config.ts").read_text(encoding="utf-8")
    assert "Tesla FP&A Agent" in config
    headline = "Tesla's quarter, forecast and explained by an agent, checked against the filings."
    assert headline in app
    disclaimer = (
        "Independent analysis built from Tesla's public SEC filings and investor-relations "
        "releases. Not affiliated with or endorsed by Tesla, Inc. Not investment advice."
    )
    assert disclaimer in config
    source_suffixes = {".tsx", ".ts", ".css", ".html", ".svg", ".json"}
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in SITE.rglob("*")
        if path.is_file()
        and path.suffix in source_suffixes
        and "node_modules" not in path.parts
        and "dist" not in path.parts
        and path.name != "package-lock.json"
    )
    lowered = combined.lower()
    assert "revolutionary" not in lowered
    assert "supercharged" not in lowered
    assert "→" not in combined
    assert not re.search(r"[\U0001F300-\U0001FAFF]", combined)
    for forbidden in FORBIDDEN_HEXES:
        assert forbidden.lower() not in lowered


def test_site_workflow_builds_without_secrets() -> None:
    text = (REPO_ROOT / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")
    assert "npm ci" in text
    assert "npm run build" in text
    assert 'node-version: "22"' in text
    assert "OPENAI_API_KEY" not in text
    assert "SEC_USER_AGENT" not in text
    for pattern in SECRET_PATTERNS:
        assert pattern.search(text) is None


def test_social_preview_points_at_a_1200_by_630_png() -> None:
    text = (SITE / "index.html").read_text(encoding="utf-8")
    base = "https://kambourr.github.io/tesla-fpa-agent/"
    og_image = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', text)
    twitter_image = re.search(r'<meta\s+name="twitter:image"\s+content="([^"]+)"', text)
    assert og_image is not None
    assert twitter_image is not None
    assert og_image.group(1) == twitter_image.group(1)
    assert og_image.group(1).startswith(base)
    assert og_image.group(1).endswith("og-image.png")
    assert re.search(r'<meta\s+name="twitter:card"\s+content="summary_large_image"', text)
    assert re.search(r'<meta\s+property="og:image:width"\s+content="1200"', text)
    assert re.search(r'<meta\s+property="og:image:height"\s+content="630"', text)

    png = (SITE / "public" / "og-image.png").read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", png[16:24])
    assert (width, height) == (1200, 630)


def test_site_tree_has_no_secret_material() -> None:
    offenders: list[str] = []
    for path in SITE.rglob("*"):
        if "node_modules" in path.parts or "dist" in path.parts:
            continue
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == []
