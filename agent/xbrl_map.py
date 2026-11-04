"""Load the XBRL tag map.

The config names the concept Tesla reported for each series, in the order a
filing should be searched. It does not download filings or pick a fact.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "config" / "xbrl_tags.json"

# Section 4 series that must be read from a filing. Free cash flow is computed.
# Deliveries and production stay in the manual CSV.
REQUIRED_METRICS = (
    "total_revenue",
    "automotive_sales",
    "automotive_regulatory_credits",
    "automotive_leasing",
    "energy_generation_and_storage",
    "services_and_other",
    "cost_of_revenue",
    "cost_of_revenue_automotive",
    "cost_of_revenue_automotive_sales",
    "cost_of_revenue_automotive_leasing",
    "cost_of_revenue_energy",
    "cost_of_revenue_services",
    "gross_profit",
    "research_and_development",
    "selling_general_and_administrative",
    "operating_expenses",
    "operating_income",
    "net_cash_from_operating_activities",
    "purchases_of_property_and_equipment",
)


class XbrlTag(BaseModel):
    """One concept, optionally narrowed to a single axis member."""

    model_config = ConfigDict(extra="forbid")

    concept: str
    axis: str | None = None
    member: str | None = None
    filed_in: str

    @model_validator(mode="after")
    def name_is_qualified_and_member_is_paired(self) -> Self:
        taxonomy, _, local = self.concept.partition(":")
        if not taxonomy or not local or ":" in local:
            raise ValueError(f"concept must be taxonomy:name, got {self.concept}")
        if (self.axis is None) != (self.member is None):
            raise ValueError(f"{self.concept} needs both an axis and a member, or neither")
        if self.axis is not None and ":" not in self.axis:
            raise ValueError(f"axis must be taxonomy:name, got {self.axis}")
        if self.member is not None and ":" not in self.member:
            raise ValueError(f"member must be taxonomy:name, got {self.member}")
        if not self.filed_in.strip():
            raise ValueError(f"{self.concept} needs filed_in")
        return self


class RejectedTag(BaseModel):
    """A concept or member that looks related and must not be read as the line."""

    model_config = ConfigDict(extra="forbid")

    concept: str
    member: str | None = None
    reason: str


class MetricSpec(BaseModel):
    """How to read one series, and what to do when none of the tags match."""

    model_config = ConfigDict(extra="forbid")

    label: str
    required: bool
    source: Literal["xbrl", "computed", "manual", "not_reported"]
    tags: list[XbrlTag]
    when_missing: str
    forecast_driver: str | None = None

    @model_validator(mode="after")
    def xbrl_metrics_have_a_tag(self) -> Self:
        if self.source == "xbrl" and not self.tags:
            raise ValueError(f"{self.label} is an XBRL metric with no tag")
        if self.source != "xbrl" and self.tags:
            raise ValueError(f"{self.label} is {self.source} and must not list a tag")
        if not self.when_missing.strip():
            raise ValueError(f"{self.label} needs when_missing")
        return self


class XbrlMap(BaseModel):
    """The committed tag map."""

    model_config = ConfigDict(extra="forbid")

    selection: str
    period_rule: str
    companyfacts_limit: str
    gaps_and_tag_changes: list[str]
    do_not_use: list[RejectedTag]
    metrics: dict[str, MetricSpec]

    @model_validator(mode="after")
    def required_metrics_have_tags(self) -> Self:
        missing = [
            name
            for name in REQUIRED_METRICS
            if name not in self.metrics
            or not self.metrics[name].required
            or not self.metrics[name].tags
        ]
        if missing:
            raise ValueError("required metric has no tag: " + ", ".join(missing))
        if not self.gaps_and_tag_changes:
            raise ValueError("gaps_and_tag_changes is empty")
        if not self.do_not_use:
            raise ValueError("do_not_use is empty")
        return self


def load_xbrl_map(path: Path | None = None) -> XbrlMap:
    """Read the tag map. Does not fetch filings."""
    source = DEFAULT_PATH if path is None else path
    payload = json.loads(source.read_text(encoding="utf-8"))
    return XbrlMap.model_validate(payload)
