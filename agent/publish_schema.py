"""The shape of ``site/public/data/dashboard.json``, locked for the static site.

The site imports ``site/src/data/dashboard.schema.json``, which is generated
from these models by ``schema_text``. ``tests/test_publish.py`` fails when the
committed file drifts from them. Money values are JSON numbers in USD, rounded
to four decimals, and ``null`` when missing. Nothing here may hold a secret.
"""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict

Unit = Literal["USD", "units", "USD_per_unit", "percent"]
Scenario = Literal["bull", "base", "bear"]
StageName = Literal["ingest", "load", "forecast", "explain", "verify", "publish"]
BridgeName = Literal["revenue", "gross_profit", "operating_income", "free_cash_flow"]
ClaimStatus = Literal["verified", "flagged", "unsupported"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Stage(_Model):
    name: StageName
    seconds: float | None


class RunMetadata(_Model):
    started_at: str | None
    duration_seconds: float | None
    stages: list[Stage]
    model: str | None
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost_usd: float | None
    data_as_of: str | None


class Filing(_Model):
    form: str
    accession: str
    filing_date: str
    url: str


class PnlLine(_Model):
    metric: str
    label: str
    unit: Unit
    forecast: float | None
    actual: float | None
    variance: float | None
    variance_pct: float | None
    favorable: bool | None


class Drivers(_Model):
    """Base forecast values the browser needs to recompute the scenarios."""

    deliveries: float | None
    automotive_asp: float | None
    gross_margin: float | None
    automotive_regulatory_credits: float | None
    automotive_leasing: float | None
    energy_generation_and_storage: float | None
    services_and_other: float | None
    operating_expenses: float | None


class BridgeBar(_Model):
    driver: str
    label: str
    value: float
    favorable: bool


class VerificationCounts(_Model):
    verified: int
    flagged: int
    unsupported: int
    total: int


class ClaimView(_Model):
    metric: str
    period: str
    value: float
    unit: str
    sentence_ref: str
    status: ClaimStatus
    expected: float | None
    expected_unit: str | None
    source: str | None
    source_url: str | None


class Memo(_Model):
    text: str
    claims: list[ClaimView]
    verification: VerificationCounts


class QuarterView(_Model):
    quarter: str
    label: str
    kind: Literal["backtest", "forward"]
    has_forecast: bool
    filing: Filing | None
    lines: list[PnlLine]
    drivers: Drivers | None
    scenarios: dict[Scenario, dict[str, float | None]]
    bridges: dict[BridgeName, list[BridgeBar]]
    memo: Memo | None


class QaAnswer(_Model):
    number: int
    question: str
    text: str
    claims: list[ClaimView]


class QaSet(_Model):
    quarter: str
    answers: list[QaAnswer]
    verification: VerificationCounts


class BacktestRow(_Model):
    quarter: str
    metric: str
    actual: float | None
    forecast: float | None
    abs_pct_error: float | None


class Backtest(_Model):
    rows: list[BacktestRow]
    averages: dict[str, float | None]


class ScenarioTriple(_Model):
    bull: float
    base: float
    bear: float


class ScenarioFlex(_Model):
    deliveries_pct: ScenarioTriple
    automotive_asp_pct: ScenarioTriple
    gross_margin_bp: ScenarioTriple


class Sources(_Model):
    """What the published numbers were built from, counted from the database."""

    facts: int
    filings: int
    delivery_quarters: int
    earliest_filing_date: str | None
    latest_filing_date: str | None


class FirstDraftCatch(_Model):
    """One figure the verifier rejected in a model's first draft, before the re-ask."""

    quarter: str
    location: str
    metric: str
    period: str
    written: float
    unit: str
    expected: float | None
    expected_unit: str | None
    status: Literal["flagged", "unsupported"]
    source: str | None


class DraftIssue(_Model):
    """A rule a draft broke other than a wrong figure (structure, length, advice wording)."""

    quarter: str
    text: str


class FirstDrafts(_Model):
    """What code caught in the model's first drafts, over the narratives that recorded it.

    ``recorded`` of ``narratives`` carry a record; the rest were drafted before
    recording began. ``rejected`` drafts had at least one problem and were sent
    back once. ``final_problems`` counts what is still flagged or unsupported
    after the re-ask, across those same narratives. ``first_issues`` lists the
    first drafts' other problems (validation issues and advice phrases);
    ``final_issues`` lists what the published drafts still break.
    """

    narratives: int
    recorded: int
    checked: int
    caught: int
    guard_hits: int
    rejected: int
    final_problems: int
    catches: list[FirstDraftCatch]
    first_issues: list[DraftIssue]
    final_issues: list[DraftIssue]


class Dashboard(_Model):
    schema_version: Literal[1]
    generated_at: str
    latest_quarter: str
    forward_forecast_published: bool
    run: RunMetadata
    last_full_run: RunMetadata | None
    quarters: list[QuarterView]
    qa: QaSet | None
    backtest: Backtest
    scenario_flex: ScenarioFlex
    sources: Sources
    first_drafts: FirstDrafts


def schema_text() -> str:
    """The JSON Schema for ``Dashboard``, with sorted keys and a trailing newline."""
    return json.dumps(Dashboard.model_json_schema(), indent=2, sort_keys=True) + "\n"
