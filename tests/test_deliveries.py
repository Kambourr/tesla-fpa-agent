"""Acceptance checks for the manual deliveries transcription (M1-T4).

The committed CSV is the last 20 production-and-deliveries releases available
on 2026-11-04, from 2021-Q4 through 2026-Q3. Each total is the Total row of
that quarter's first investor-relations release, the same figure printed in
the same-day Form 8-K Exhibit 99.1. Later shareholder updates are not a source.
"""

import ast
import csv
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DELIVERIES_PATH = REPO_ROOT / "data" / "manual" / "deliveries.csv"
COLUMNS = (
    "quarter",
    "production_total",
    "deliveries_total",
    "release_date",
    "source_url",
)

# (quarter, production_total, deliveries_total, release_date, source_url)
# Totals are the first-release table, not the rounded sentence above it.
FIRST_RELEASE = (
    (
        "2021-Q4",
        305_840,
        308_600,
        "2022-01-02",
        "https://ir.tesla.com/press-release/tesla-q4-2021-vehicle-production-deliveries",
    ),
    (
        "2022-Q1",
        305_407,
        310_048,
        "2022-04-02",
        "https://ir.tesla.com/press-release/"
        "tesla-vehicle-production-deliveries-and-date-financial-results-webcast-first-quarter",
    ),
    (
        "2022-Q2",
        258_580,
        254_695,
        "2022-07-02",
        "https://ir.tesla.com/press-release/"
        "tesla-vehicle-production-deliveries-and-date-financial-results-webcast-second-quarter",
    ),
    (
        "2022-Q3",
        365_923,
        343_830,
        "2022-10-02",
        "https://ir.tesla.com/press-release/"
        "tesla-vehicle-production-deliveries-and-date-financial-results-webcast-third-quarter",
    ),
    (
        "2022-Q4",
        439_701,
        405_278,
        "2023-01-02",
        "https://ir.tesla.com/press-release/"
        "tesla-vehicle-production-deliveries-and-date-financial-results-webcast-fourth-quarter",
    ),
    (
        "2023-Q1",
        440_808,
        422_875,
        "2023-04-02",
        "https://ir.tesla.com/press-release/"
        "tesla-vehicle-production-deliveries-and-date-financial-results-webcast-first-quarter-2023",
    ),
    (
        "2023-Q2",
        479_700,
        466_140,
        "2023-07-02",
        "https://ir.tesla.com/press-release/"
        "tesla-vehicle-production-deliveries-and-date-financial-results-webcast-second-quarter-2023",
    ),
    (
        "2023-Q3",
        430_488,
        435_059,
        "2023-10-02",
        "https://ir.tesla.com/press-release/"
        "tesla-vehicle-production-deliveries-and-date-financial-results-webcast-third-quarter-2023",
    ),
    (
        "2023-Q4",
        494_989,
        484_507,
        "2024-01-02",
        "https://ir.tesla.com/press-release/"
        "tesla-vehicle-production-deliveries-and-date-financial-results-webcast-fourth-quarter-2023",
    ),
    (
        "2024-Q1",
        433_371,
        386_810,
        "2024-04-02",
        "https://ir.tesla.com/press-release/"
        "tesla-vehicle-production-deliveries-and-date-financial-results-webcast-first-quarter-2024",
    ),
    (
        "2024-Q2",
        410_831,
        443_956,
        "2024-07-02",
        "https://ir.tesla.com/press-release/"
        "tesla-vehicle-production-deliveries-and-date-financial-results-webcast-second-quarter-2024",
    ),
    (
        "2024-Q3",
        469_796,
        462_890,
        "2024-10-02",
        "https://ir.tesla.com/press-release/"
        "tesla-third-quarter-2024-production-deliveries-and-deployments",
    ),
    (
        "2024-Q4",
        459_445,
        495_570,
        "2025-01-02",
        "https://ir.tesla.com/press-release/"
        "tesla-fourth-quarter-2024-production-deliveries-and-deployments",
    ),
    (
        "2025-Q1",
        362_615,
        336_681,
        "2025-04-02",
        "https://ir.tesla.com/press-release/"
        "tesla-first-quarter-2025-production-deliveries-and-deployments",
    ),
    (
        "2025-Q2",
        410_244,
        384_122,
        "2025-07-02",
        "https://ir.tesla.com/press-release/"
        "tesla-second-quarter-2025-production-deliveries-deployments",
    ),
    (
        "2025-Q3",
        447_450,
        497_099,
        "2025-10-02",
        "https://ir.tesla.com/press-release/"
        "tesla-third-quarter-2025-production-deliveries-deployments",
    ),
    (
        "2025-Q4",
        434_358,
        418_227,
        "2026-01-02",
        "https://ir.tesla.com/press-release/"
        "tesla-fourth-quarter-2025-production-deliveries-deployments",
    ),
    (
        "2026-Q1",
        408_386,
        358_023,
        "2026-04-02",
        "https://ir.tesla.com/press-release/"
        "tesla-first-quarter-2026-production-deliveries-and-deployments",
    ),
    (
        "2026-Q2",
        451_758,
        480_126,
        "2026-07-02",
        "https://ir.tesla.com/press-release/"
        "tesla-second-quarter-2026-production-deliveries-and-deployments",
    ),
    (
        "2026-Q3",
        464_391,
        486_532,
        "2026-10-02",
        "https://ir.tesla.com/press-release/"
        "tesla-third-quarter-2026-production-deliveries-and-deployments",
    ),
)

# Annual Total row on that year's Q4 production-and-deliveries release.
ANNUAL_TOTALS_ON_Q4_RELEASE = {
    2022: (1_369_611, 1_313_851),
    2023: (1_845_985, 1_808_581),
    2024: (1_773_443, 1_789_226),
    2025: (1_654_667, 1_636_129),
}

RELEASE_MONTH_AFTER_QUARTER = {1: 4, 2: 7, 3: 10, 4: 1}


def _text() -> str:
    return DELIVERIES_PATH.read_text(encoding="utf-8")


def _rows() -> list[dict[str, str]]:
    with DELIVERIES_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(COLUMNS)
        return list(reader)


def _quarter_index(label: str) -> tuple[int, int]:
    year_text, quarter_text = label.split("-Q")
    return int(year_text), int(quarter_text)


def test_file_has_the_required_columns_and_nothing_else() -> None:
    rows = _rows()
    assert len(rows) == 20
    assert len(FIRST_RELEASE) == 20
    for row in rows:
        assert list(row) == list(COLUMNS)


def test_twenty_quarters_are_contiguous_and_ordered() -> None:
    labels = [row["quarter"] for row in _rows()]
    parsed = [_quarter_index(label) for label in labels]
    ordinals = [year * 4 + quarter for year, quarter in parsed]
    assert ordinals == list(range(ordinals[0], ordinals[0] + 20))
    assert labels == [quarter for quarter, *_rest in FIRST_RELEASE]
    assert labels[0] == "2021-Q4"
    assert labels[-1] == "2026-Q3"
    assert len(set(labels)) == 20


def test_totals_are_the_first_release_table_not_a_later_revision() -> None:
    """A later shareholder letter or a rounded headline must not replace the table."""
    rows = _rows()
    for row, expected in zip(rows, FIRST_RELEASE, strict=True):
        quarter, production, deliveries, release_date, source_url = expected
        assert row["quarter"] == quarter
        assert row["production_total"] == str(production)
        assert row["deliveries_total"] == str(deliveries)
        assert int(row["production_total"]) == production
        assert int(row["deliveries_total"]) == deliveries
        assert row["release_date"] == release_date
        assert row["source_url"] == source_url


def test_every_row_has_a_release_date_and_a_source_url() -> None:
    for row in _rows():
        year, quarter = _quarter_index(row["quarter"])
        released = date.fromisoformat(row["release_date"])
        assert row["release_date"]
        assert row["source_url"].startswith("https://ir.tesla.com/press-release/")
        assert "production" in row["source_url"]
        assert "deliveries" in row["source_url"]
        assert "?" not in row["source_url"]
        assert row["source_url"].count("://") == 1
        expected_month = RELEASE_MONTH_AFTER_QUARTER[quarter]
        expected_year = year + 1 if quarter == 4 else year
        assert released == date(expected_year, expected_month, 2)


def test_source_urls_point_at_the_production_release() -> None:
    """Each URL is that quarter's production-and-deliveries page, not an earnings release."""
    urls = [row["source_url"] for row in _rows()]
    assert len(set(urls)) == 20
    for url in urls:
        slug = url.removeprefix("https://ir.tesla.com/press-release/")
        assert slug
        assert "/" not in slug
        assert not slug.endswith((".pdf", ".html", ".htm"))
        assert "sec.gov" not in url
        assert slug.startswith("tesla-")
        assert "production" in slug
        assert "deliveries" in slug


def test_full_years_sum_to_the_annual_table_on_that_q4_release() -> None:
    by_year: dict[int, list[tuple[int, int]]] = {}
    for row in _rows():
        year, _quarter = _quarter_index(row["quarter"])
        by_year.setdefault(year, []).append(
            (int(row["production_total"]), int(row["deliveries_total"]))
        )
    for year, (production, deliveries) in ANNUAL_TOTALS_ON_Q4_RELEASE.items():
        quarters = by_year[year]
        assert len(quarters) == 4
        assert sum(item[0] for item in quarters) == production
        assert sum(item[1] for item in quarters) == deliveries


def test_csv_is_plain_text_without_secrets() -> None:
    text = _text()
    assert text.startswith("quarter,production_total,deliveries_total,release_date,source_url\n")
    assert text.endswith("\n")
    assert "\r" not in text
    assert "@" not in text
    assert "sk-" not in text
    assert "BEGIN " not in text


def test_pipeline_code_does_not_fetch_delivery_pages() -> None:
    """Ingest must not scrape investor-relations pages. The CSV is manual source data."""
    agent_dir = REPO_ROOT / "agent"
    offenders: list[str] = []
    for path in sorted(agent_dir.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                value = node.value.lower()
                if "ir.tesla.com" in value or "tesla.com/press" in value:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}")
    assert offenders == []
