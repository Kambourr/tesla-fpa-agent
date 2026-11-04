"""Load companyfacts and the deliveries CSV into DuckDB.

`python -m agent ingest` is the command. `--fixtures` reads local JSON and
does not call the SEC. The live path uses the cached SEC client. Neither
path prints a secret, and neither path fetches an investor-relations page.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

from agent.actuals import assemble_quarter_actuals, facts_from_companyfacts, store_reported_facts
from agent.deliveries import default_csv_path, load_deliveries, repo_root, validate_deliveries
from agent.forecast_config import load_forecast_config
from agent.schema import apply_schema
from agent.sec import SecClient
from agent.xbrl_map import load_xbrl_map

PUBLISHED_QUARTERS = 12


class IngestError(Exception):
    """The load stopped before the database held a usable series."""


def default_database_path() -> Path:
    return repo_root() / "data" / "fpa.duckdb"


def forecast_history_quarters() -> int:
    """How many quarters before the oldest published quarter the formulas read.

    The deepest `input_offsets` entry is the history the forecast needs.
    The current config reaches five quarters back.
    """
    config = load_forecast_config()
    return max(abs(offset) for driver in config.drivers.values() for offset in driver.input_offsets)


def quarter_window(latest: str, count: int) -> list[str]:
    """`count` quarter labels ending at `latest`, oldest first."""
    year_text, quarter_text = latest.split("-Q")
    year = int(year_text)
    quarter = int(quarter_text)
    labels: list[str] = []
    for _ in range(count):
        labels.append(f"{year}-Q{quarter}")
        quarter -= 1
        if quarter == 0:
            quarter = 4
            year -= 1
    return list(reversed(labels))


def run_ingest(
    *,
    database: Path,
    csv_path: Path | None = None,
    fixtures: Path | None = None,
) -> None:
    """Validate deliveries, then store filings, quarters, and the CSV.

    Fixture mode reads `companyfacts.json` and `submissions.json` from
    `fixtures`. Without that directory the SEC client reads its cache or
    the live feed. Source pages are not requested.
    """
    source = default_csv_path() if csv_path is None else csv_path
    issues = validate_deliveries(source)
    if issues:
        raise IngestError("\n".join(issues))
    companyfacts, submissions = _load_filings(fixtures)
    facts = facts_from_companyfacts(companyfacts, submissions, load_xbrl_map())
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(database))
    try:
        apply_schema(connection)
        store_reported_facts(connection, facts)
        assemble_quarter_actuals(connection)
        _replace_deliveries(connection, source)
        _require_window(connection)
    finally:
        connection.close()
    print(
        f"ingest wrote {len(facts)} facts to {database.name}",
        flush=True,
    )


def _load_filings(fixtures: Path | None) -> tuple[dict, dict]:
    if fixtures is None:
        client = SecClient.from_settings()
        return json.loads(client.companyfacts()), json.loads(client.filing_index())
    companyfacts_path = fixtures / "companyfacts.json"
    submissions_path = fixtures / "submissions.json"
    if not companyfacts_path.is_file() or not submissions_path.is_file():
        raise IngestError(f"{fixtures} needs companyfacts.json and submissions.json")
    return (
        json.loads(companyfacts_path.read_text(encoding="utf-8")),
        json.loads(submissions_path.read_text(encoding="utf-8")),
    )


def _replace_deliveries(connection: duckdb.DuckDBPyConnection, csv_path: Path) -> None:
    connection.execute("DELETE FROM deliveries")
    for row in load_deliveries(csv_path):
        connection.execute(
            "INSERT INTO deliveries VALUES (?, ?, ?, ?, ?)",
            [
                row.quarter,
                row.production_total,
                row.deliveries_total,
                row.release_date,
                row.source_url,
            ],
        )


def _require_window(connection: duckdb.DuckDBPyConnection) -> None:
    present = {
        row[0]
        for row in connection.execute(
            "SELECT DISTINCT quarter FROM quarter_actual WHERE metric = 'total_revenue'"
        ).fetchall()
    }
    if not present:
        raise IngestError("no total_revenue quarters were stored")
    needed = quarter_window(max(present), PUBLISHED_QUARTERS + forecast_history_quarters())
    missing = [label for label in needed if label not in present]
    if missing:
        raise IngestError("quarter_actual is missing " + ", ".join(missing))
    stored = {row[0] for row in connection.execute("SELECT quarter FROM deliveries").fetchall()}
    missing_deliveries = [label for label in needed if label not in stored]
    if missing_deliveries:
        raise IngestError("deliveries is missing " + ", ".join(missing_deliveries))
