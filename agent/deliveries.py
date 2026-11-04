"""Structural checks for the manual deliveries file, and page-text matching.

`validate_deliveries` is the check a normal ingest run can call. It reads the
CSV and does not open a network connection. Fetching a source page is a
separate function, used only when `scripts/check_deliveries` is pointed at a
live URL.
"""

from __future__ import annotations

import csv
import re
import urllib.request
from dataclasses import dataclass
from html import unescape
from pathlib import Path

COLUMNS = (
    "quarter",
    "production_total",
    "deliveries_total",
    "release_date",
    "source_url",
)

# Larger than the biggest move in the transcribed series (production rose 41.5%
# from 2022-Q2 to 2022-Q3) and still tight enough to reject a halved or doubled quarter.
MAX_PLAUSIBLE_QOQ_CHANGE = 0.50

_QUARTER = re.compile(r"^(\d{4})-Q([1-4])$")
_BLOCK_TAG = re.compile(
    r"</?(?:td|th|tr|table|p|div|br|li|h[1-6])\b[^>]*>",
    re.IGNORECASE,
)
_TAG = re.compile(r"<[^>]+>")
_FETCH_USER_AGENT = "tesla-fpa-agent/0.1 deliveries-check"


@dataclass(frozen=True)
class DeliveryRow:
    quarter: str
    year: int
    quarter_number: int
    production_total: int
    deliveries_total: int
    release_date: str
    source_url: str


@dataclass(frozen=True)
class PageCheck:
    quarter: str
    production_total: int
    deliveries_total: int
    production_found: bool
    deliveries_found: bool
    error: str = ""

    @property
    def matched(self) -> bool:
        return self.error == "" and self.production_found and self.deliveries_found


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_csv_path() -> Path:
    return repo_root() / "data" / "manual" / "deliveries.csv"


def load_deliveries(path: Path) -> list[DeliveryRow]:
    """Read rows after the header check. Structural problems stay in `validate_deliveries`."""
    rows, issues = _load_rows(path)
    if issues:
        raise ValueError("\n".join(issues))
    return rows


def validate_deliveries(path: Path) -> list[str]:
    """Return structural problems. An empty list means the file passes.

    This never fetches source pages.
    """
    rows, issues = _load_rows(path)
    issues.extend(_sequence_issues(rows))
    return issues


def page_text(html: str) -> str:
    """Drop tags so a figure split by inline markup can still be read as digits.

    Table cells are separated first, so two adjacent totals do not glue together.
    Inline tags such as ``<b>`` are removed without inserting a space.
    """
    return unescape(_TAG.sub("", _BLOCK_TAG.sub(" ", html)))


def figure_in_text(text: str, value: int) -> bool:
    """True when the page shows the figure with or without thousands separators.

    A longer grouped number such as 1,433,371 does not count as 433,371.
    """
    plain = page_text(text)
    grouped = f"{value:,}"
    patterns = (
        rf"(?<![\d,]){re.escape(grouped)}(?![\d,])",
        rf"(?<!\d){value}(?!\d)",
    )
    return any(re.search(pattern, plain) for pattern in patterns)


def check_page(row: DeliveryRow, html: str) -> PageCheck:
    return PageCheck(
        quarter=row.quarter,
        production_total=row.production_total,
        deliveries_total=row.deliveries_total,
        production_found=figure_in_text(html, row.production_total),
        deliveries_found=figure_in_text(html, row.deliveries_total),
    )


def fetch_source_page(url: str, timeout: float = 30.0) -> str:
    """GET one release page. Callers must opt in. Ingest does not call this."""
    request = urllib.request.Request(url, headers={"User-Agent": _FETCH_USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
    return raw.decode(charset, errors="replace")


def format_structural_report(issues: list[str]) -> str:
    if not issues:
        return "structural OK"
    return "\n".join(issues)


def format_page_report(check: PageCheck) -> str:
    if check.error:
        return f"FETCH_FAILED {check.quarter} {check.error}"
    if check.matched:
        return (
            f"MATCH {check.quarter} "
            f"production {check.production_total} deliveries {check.deliveries_total}"
        )
    missing: list[str] = []
    if not check.production_found:
        missing.append(f"production {check.production_total}")
    if not check.deliveries_found:
        missing.append(f"deliveries {check.deliveries_total}")
    return f"MISMATCH {check.quarter} missing " + " and ".join(missing)


def _load_rows(path: Path) -> tuple[list[DeliveryRow], list[str]]:
    issues: list[str] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(COLUMNS):
            found = reader.fieldnames
            return [], [f"unexpected columns: {found}"]
        rows: list[DeliveryRow] = []
        for raw in reader:
            rows.append(_parse_row(raw, issues))
    return rows, issues


def _parse_row(raw: dict[str, str], issues: list[str]) -> DeliveryRow:
    label = (raw.get("quarter") or "").strip()
    match = _QUARTER.fullmatch(label)
    if match is None:
        issues.append(f"unreadable quarter {label!r}")
        year, quarter_number = 0, 0
    else:
        year, quarter_number = int(match.group(1)), int(match.group(2))

    production = _parse_count(raw.get("production_total"), label, "production_total", issues)
    deliveries = _parse_count(raw.get("deliveries_total"), label, "deliveries_total", issues)
    release_date = (raw.get("release_date") or "").strip()
    source_url = (raw.get("source_url") or "").strip()
    if not release_date:
        issues.append(f"missing release date for {label or 'row'}")
    if not source_url.startswith(("https://", "http://")):
        issues.append(f"missing source for {label or 'row'}")

    return DeliveryRow(
        quarter=label,
        year=year,
        quarter_number=quarter_number,
        production_total=production,
        deliveries_total=deliveries,
        release_date=release_date,
        source_url=source_url,
    )


def _parse_count(value: str | None, quarter: str, column: str, issues: list[str]) -> int:
    text = (value or "").strip()
    if not text.isdigit():
        issues.append(f"unreadable {column} for {quarter or 'row'}")
        return 0
    return int(text)


def _sequence_issues(rows: list[DeliveryRow]) -> list[str]:
    issues: list[str] = []
    previous: DeliveryRow | None = None
    for row in rows:
        if row.year == 0:
            previous = None
            continue
        if previous is not None and previous.year != 0:
            expected = _next_quarter(previous.year, previous.quarter_number)
            actual = (row.year, row.quarter_number)
            if actual == (previous.year, previous.quarter_number):
                issues.append(f"duplicate quarter {row.quarter}")
            elif actual != expected:
                issues.append(f"quarter gap between {previous.quarter} and {row.quarter}")
            else:
                issues.extend(_qoq_issues(previous, row))
        previous = row
    return issues


def _qoq_issues(previous: DeliveryRow, row: DeliveryRow) -> list[str]:
    issues: list[str] = []
    for metric, before, after in (
        ("production", previous.production_total, row.production_total),
        ("deliveries", previous.deliveries_total, row.deliveries_total),
    ):
        if before <= 0 or after <= 0 or _change_is_implausible(before, after):
            issues.append(
                f"implausible quarter-over-quarter change in {metric} "
                f"for {row.quarter}: {before} to {after}"
            )
    return issues


def _change_is_implausible(previous: int, current: int) -> bool:
    """True when the move is strictly larger than MAX_PLAUSIBLE_QOQ_CHANGE."""
    scaled_limit = int(MAX_PLAUSIBLE_QOQ_CHANGE * 1000)
    return abs(current - previous) * 1000 > previous * scaled_limit


def _next_quarter(year: int, quarter_number: int) -> tuple[int, int]:
    if quarter_number == 4:
        return year + 1, 1
    return year, quarter_number + 1
