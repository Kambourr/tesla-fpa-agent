"""`python -m agent ingest` loads filings, quarters, and deliveries."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

import duckdb
import pytest

from agent.deliveries import default_csv_path, repo_root
from agent.ingest import (
    PUBLISHED_QUARTERS,
    IngestError,
    forecast_history_quarters,
    quarter_window,
    run_ingest,
)


def _bounds(year: int, quarter: int) -> tuple[str, str]:
    starts = {1: "01-01", 2: "04-01", 3: "07-01", 4: "10-01"}
    ends = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}
    return f"{year}-{starts[quarter]}", f"{year}-{ends[quarter]}"


def _filed(year: int, quarter: int) -> str:
    months = {1: "04-20", 2: "07-20", 3: "10-20"}
    return f"{year}-{months[quarter]}"


def write_filings(directory: Path) -> None:
    """Companyfacts covering 2022-Q1 through 2026-Q3, plus one restatement."""
    facts: list[dict[str, object]] = []
    accessions: list[str] = []
    forms: list[str] = []
    filing_dates: list[str] = []
    report_dates: list[str] = []
    documents: list[str] = []
    number = 1

    def add_filing(
        form: str,
        year: int,
        report: str,
        filed: str,
        periods: list[tuple[str, str, int]],
    ) -> None:
        nonlocal number
        accession = f"0001628280-{year % 100:02d}-{number:06d}"
        number += 1
        accessions.append(accession)
        forms.append(form)
        report_dates.append(report)
        filing_dates.append(filed)
        documents.append(f"tsla-{report.replace('-', '')}.htm")
        fiscal = "FY" if form == "10-K" else f"Q{int(report[6])}"
        for start, end, value in periods:
            facts.append(
                {
                    "accn": accession,
                    "start": start,
                    "end": end,
                    "val": value,
                    "form": form,
                    "fy": year,
                    "fp": fiscal,
                    "filed": filed,
                }
            )

    for year in range(2022, 2027):
        for quarter in (1, 2, 3):
            start, end = _bounds(year, quarter)
            periods = [(start, end, year * 10 + quarter)]
            if year == 2022 and quarter == 2:
                periods.append(("2022-01-01", "2022-03-31", 1))
            add_filing("10-Q", year, end, _filed(year, quarter), periods)
        if year == 2026:
            continue
        annual = sum(year * 10 + quarter for quarter in (1, 2, 3, 4))
        add_filing(
            "10-K",
            year,
            f"{year}-12-31",
            f"{year + 1}-01-25",
            [(f"{year}-01-01", f"{year}-12-31", annual)],
        )
    directory.mkdir()
    companyfacts = {
        "cik": 1318605,
        "entityName": "Tesla, Inc.",
        "facts": {"us-gaap": {"Revenues": {"units": {"USD": facts}}}},
    }
    submissions = {
        "cik": "0001318605",
        "filings": {
            "recent": {
                "accessionNumber": accessions,
                "form": forms,
                "filingDate": filing_dates,
                "reportDate": report_dates,
                "primaryDocument": documents,
            }
        },
    }
    (directory / "companyfacts.json").write_text(json.dumps(companyfacts), encoding="utf-8")
    (directory / "submissions.json").write_text(json.dumps(submissions), encoding="utf-8")


def _block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("ingest opened the network")

    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    monkeypatch.setattr("agent.deliveries.fetch_source_page", refuse)
    monkeypatch.setattr(
        "agent.ingest.SecClient.from_settings",
        lambda *_args, **_kwargs: refuse(),
    )


def test_ingest_loads_the_window_and_keeps_the_restatement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _block_network(monkeypatch)
    fixtures = tmp_path / "sec"
    write_filings(fixtures)
    database = tmp_path / "fpa.duckdb"
    run_ingest(database=database, csv_path=default_csv_path(), fixtures=fixtures)
    run_ingest(database=database, csv_path=default_csv_path(), fixtures=fixtures)

    connection = duckdb.connect(str(database))
    quarters = {
        row[0]
        for row in connection.execute(
            "SELECT quarter FROM quarter_actual WHERE metric = 'total_revenue'"
        ).fetchall()
    }
    latest = max(quarters)
    needed = quarter_window(latest, PUBLISHED_QUARTERS + forecast_history_quarters())
    assert latest == "2026-Q3"
    assert set(needed) <= quarters
    assert "2022-Q1" in quarters

    first = connection.execute(
        """
        SELECT value, basis, accession, filing_date, filing_url
        FROM quarter_actual
        WHERE quarter = '2022-Q1' AND metric = 'total_revenue'
        """
    ).fetchone()
    assert first is not None
    assert int(first[0]) == 20221
    assert first[1] == "first_reported"
    assert first[2]
    assert first[3] is not None
    assert str(first[4]).startswith("https://www.sec.gov/Archives/edgar/data/1318605/")

    q4 = connection.execute(
        """
        SELECT value, basis FROM quarter_actual
        WHERE quarter = '2022-Q4' AND metric = 'total_revenue'
        """
    ).fetchone()
    assert q4 is not None
    assert int(q4[0]) == 20224
    assert q4[1] == "derived_q4"

    restated = connection.execute(
        """
        SELECT COUNT(*) FROM fact
        WHERE metric = 'total_revenue'
          AND period_start = DATE '2022-01-01'
          AND period_end = DATE '2022-03-31'
        """
    ).fetchone()
    assert restated == (2,)

    blank = connection.execute(
        """
        SELECT COUNT(*) FROM fact_with_source
        WHERE accession IS NULL
           OR filing_date IS NULL
           OR filing_url IS NULL
           OR filing_url = ''
        """
    ).fetchone()
    assert blank == (0,)

    deliveries = connection.execute("SELECT COUNT(*) FROM deliveries").fetchone()
    assert deliveries == (20,)
    connection.close()


def test_invalid_deliveries_does_not_open_the_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _block_network(monkeypatch)
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text(
        "quarter,production_total,deliveries_total,release_date,source_url\n"
        "2024-Q1,10,10,2024-04-02,https://example.com/q1\n"
        "2024-Q3,10,10,2024-10-02,https://example.com/q3\n",
        encoding="utf-8",
    )
    database = tmp_path / "fpa.duckdb"
    with pytest.raises(IngestError, match="gap"):
        run_ingest(database=database, csv_path=csv_path, fixtures=tmp_path / "missing")
    assert not database.exists()


def test_cli_prints_no_secret(tmp_path: Path) -> None:
    fixtures = tmp_path / "sec"
    write_filings(fixtures)
    database = tmp_path / "nested" / "fpa.duckdb"
    secret = "sec-contact-secret-do-not-print"
    key = "openai-key-value-do-not-print"
    env = os.environ.copy()
    env["SEC_USER_AGENT"] = secret
    env["OPENAI_API_KEY"] = key
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "agent",
            "ingest",
            "--fixtures",
            str(fixtures),
            "--database",
            str(database),
            "--csv",
            str(default_csv_path()),
        ],
        cwd=repo_root(),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    combined = result.stdout + result.stderr
    assert secret not in combined
    assert key not in combined
    assert "facts" in result.stdout
    assert database.is_file()
