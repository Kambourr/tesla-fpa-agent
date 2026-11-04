"""M1-T5: page checks against saved fixtures, and structural checks with no network."""

from __future__ import annotations

import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

from agent.deliveries import (
    MAX_PLAUSIBLE_QOQ_CHANGE,
    fetch_source_page,
    figure_in_text,
    validate_deliveries,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_deliveries"
COMMITTED = REPO_ROOT / "data" / "manual" / "deliveries.csv"
HEADER = "quarter,production_total,deliveries_total,release_date,source_url"

# A page that shows the Total row the way Tesla prints it, including a tag
# inside one figure, and a larger number that must not count as a match.
MATCH_PAGE = """
<html><body>
<p>In the quarter we produced over 433,000 vehicles.</p>
<table>
<tr><td>Model 3/Y</td><td>412,376</td><td>369,783</td></tr>
<tr><td>Total</td><td>433,3<b>7</b>1</td><td>386,810</td></tr>
</table>
<p>Inventory reference 1,433,371 should not satisfy a search for the total.</p>
</body></html>
"""

MISMATCH_PAGE = """
<html><body>
<table><tr><td>Total</td><td>100,000</td><td>386,810</td></tr></table>
</body></html>
"""


def _write_csv(path: Path, rows: list[str]) -> None:
    path.write_text(HEADER + "\n" + "\n".join(rows) + "\n", encoding="utf-8")


def _run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_saved_page_fixture_matches_when_both_figures_are_present(tmp_path: Path) -> None:
    csv_path = tmp_path / "deliveries.csv"
    pages = tmp_path / "pages"
    pages.mkdir()
    _write_csv(
        csv_path,
        ["2024-Q1,433371,386810,2024-04-02,https://example.com/q1"],
    )
    (pages / "2024-Q1.html").write_text(MATCH_PAGE, encoding="utf-8")

    assert figure_in_text(MATCH_PAGE, 433_371)
    assert figure_in_text(MATCH_PAGE, 386_810)
    assert not figure_in_text("Total 1,433,371 only", 433_371)

    result = _run_script("--csv", str(csv_path), "--pages-dir", str(pages))
    assert result.returncode == 0, result.stderr
    assert "structural OK" in result.stdout
    assert "MATCH 2024-Q1 production 433371 deliveries 386810" in result.stdout
    assert "MISMATCH" not in result.stdout


def test_saved_page_fixture_reports_a_mismatch_when_a_figure_is_absent(tmp_path: Path) -> None:
    csv_path = tmp_path / "deliveries.csv"
    pages = tmp_path / "pages"
    pages.mkdir()
    _write_csv(
        csv_path,
        ["2024-Q1,433371,386810,2024-04-02,https://example.com/q1"],
    )
    (pages / "2024-Q1.html").write_text(MISMATCH_PAGE, encoding="utf-8")

    result = _run_script("--csv", str(csv_path), "--pages-dir", str(pages))
    assert result.returncode == 1
    assert "MISMATCH 2024-Q1 missing production 433371" in result.stdout
    assert not any(line.startswith("MATCH ") for line in result.stdout.splitlines())


def test_structural_check_fails_a_quarter_gap(tmp_path: Path) -> None:
    csv_path = tmp_path / "deliveries.csv"
    _write_csv(
        csv_path,
        [
            "2024-Q1,433371,386810,2024-04-02,https://example.com/q1",
            "2024-Q3,469796,462890,2024-10-02,https://example.com/q3",
        ],
    )
    issues = validate_deliveries(csv_path)
    assert any(issue.startswith("quarter gap between 2024-Q1 and 2024-Q3") for issue in issues)
    result = _run_script("--csv", str(csv_path))
    assert result.returncode == 1
    assert "quarter gap" in result.stdout


def test_structural_check_fails_a_missing_source(tmp_path: Path) -> None:
    csv_path = tmp_path / "deliveries.csv"
    _write_csv(
        csv_path,
        ["2024-Q1,433371,386810,2024-04-02,"],
    )
    issues = validate_deliveries(csv_path)
    assert "missing source for 2024-Q1" in issues
    result = _run_script("--csv", str(csv_path))
    assert result.returncode == 1
    assert "missing source for 2024-Q1" in result.stdout


def test_structural_check_fails_an_implausible_quarter_over_quarter_change(tmp_path: Path) -> None:
    csv_path = tmp_path / "deliveries.csv"
    _write_csv(
        csv_path,
        [
            "2024-Q1,400000,400000,2024-04-02,https://example.com/q1",
            "2024-Q2,400000,100000,2024-07-02,https://example.com/q2",
        ],
    )
    issues = validate_deliveries(csv_path)
    assert any("implausible quarter-over-quarter change in deliveries" in issue for issue in issues)
    assert not any("production" in issue and "implausible" in issue for issue in issues)
    result = _run_script("--csv", str(csv_path))
    assert result.returncode == 1
    assert "implausible quarter-over-quarter change" in result.stdout


def test_committed_csv_passes_structural_checks_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("structural validation must not open the network")

    monkeypatch.setattr(urllib.request, "urlopen", refuse_network)
    assert validate_deliveries(COMMITTED) == []
    result = _run_script("--csv", str(COMMITTED))
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "structural OK"
    assert "MATCH" not in result.stdout
    assert "http" not in result.stdout


def test_committed_series_stays_inside_the_plausible_change_limit() -> None:
    """The 50% bar sits above the real 2022-Q3 rebound, so the committed file passes."""
    assert MAX_PLAUSIBLE_QOQ_CHANGE == 0.50
    assert validate_deliveries(COMMITTED) == []


def test_fetch_source_page_uses_the_given_url_and_no_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Headers:
        @staticmethod
        def get_content_charset() -> str:
            return "utf-8"

    class Response:
        headers = Headers()

        def read(self) -> bytes:
            return b"<p>433,371</p>"

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

    seen: dict[str, object] = {}

    def fake_urlopen(request: urllib.request.Request, timeout: float = 0) -> Response:
        seen["url"] = request.full_url
        seen["ua"] = request.get_header("User-agent")
        seen["timeout"] = timeout
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert "433,371" in fetch_source_page("https://example.com/q", timeout=5)
    assert seen == {
        "url": "https://example.com/q",
        "ua": "tesla-fpa-agent/0.1 deliveries-check",
        "timeout": 5,
    }
    assert "@" not in str(seen["ua"])


def test_package_ingest_path_does_not_scrape_source_pages() -> None:
    """Ingest must not fetch delivery pages. The SEC client may still call urlopen."""
    agent_dir = REPO_ROOT / "agent"
    offenders: list[str] = []
    for path in sorted(agent_dir.rglob("*.py")):
        if path.name == "deliveries.py":
            continue
        source = path.read_text(encoding="utf-8")
        if "fetch_source_page" in source or "ir.tesla.com" in source:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == []
