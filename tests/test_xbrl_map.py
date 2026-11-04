"""The XBRL map covers every required series, and a missing tag fails the load."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from agent.xbrl_map import REQUIRED_METRICS, load_xbrl_map

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "config" / "xbrl_tags.json"


def test_required_metrics_have_tags() -> None:
    config = load_xbrl_map()
    assert set(REQUIRED_METRICS) <= set(config.metrics)
    for name in REQUIRED_METRICS:
        metric = config.metrics[name]
        assert metric.required, name
        assert metric.source == "xbrl", name
        assert metric.tags, name
        assert metric.when_missing.strip(), name


def test_loader_rejects_a_required_metric_with_no_tag(tmp_path: Path) -> None:
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    payload["metrics"]["total_revenue"]["tags"] = []
    path = tmp_path / "xbrl_tags.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValidationError, match="no tag"):
        load_xbrl_map(path)


def test_automotive_sales_keeps_the_three_reported_representations() -> None:
    tags = load_xbrl_map().metrics["automotive_sales"].tags
    assert [(tag.concept, tag.member) for tag in tags] == [
        ("tsla:AutomotiveSalesRevenue", "tsla:AutomotiveRevenuesMember"),
        (
            "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
            "tsla:AutomotiveSalesMember",
        ),
        (
            "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
            "us-gaap:AutomobilesMember",
        ),
    ]


def test_segment_cost_tries_cost_of_revenue_before_the_2022_cogs_tag() -> None:
    energy = load_xbrl_map().metrics["cost_of_revenue_energy"].tags
    assert [tag.concept for tag in energy] == [
        "us-gaap:CostOfRevenue",
        "us-gaap:CostOfGoodsAndServicesSold",
    ]
    assert energy[0].member == "tsla:EnergyGenerationAndStorageMember"
    assert energy[1].member == "tsla:EnergyGenerationAndStorageMember"


def test_rejected_tags_are_not_used() -> None:
    config = load_xbrl_map()
    used = {(tag.concept, tag.member) for metric in config.metrics.values() for tag in metric.tags}
    for rejected in config.do_not_use:
        assert (rejected.concept, rejected.member) not in used
        if rejected.member is None:
            assert rejected.concept not in {concept for concept, _member in used}


def test_gaps_record_the_tag_change_and_the_companyfacts_limit() -> None:
    config = load_xbrl_map()
    text = " ".join(config.gaps_and_tag_changes)
    assert "AutomobilesMember" in text
    assert "AutomotiveSalesRevenue" in text
    assert "AutomotiveSalesMember" in text
    assert "companyfacts" in config.companyfacts_limit
    assert "no tsla concepts" in config.companyfacts_limit
    assert config.metrics["free_cash_flow"].source == "computed"
    assert config.metrics["free_cash_flow"].tags == []
    assert config.metrics["deliveries"].source == "manual"
    assert config.metrics["production"].source == "manual"
    assert config.metrics["automotive_regulatory_credits_cost"].source == "not_reported"


def test_cash_flow_tags_are_the_reported_amounts() -> None:
    config = load_xbrl_map()
    cash = config.metrics["net_cash_from_operating_activities"]
    capex = config.metrics["purchases_of_property_and_equipment"]
    assert cash.tags[0].concept == "us-gaap:NetCashProvidedByUsedInOperatingActivities"
    assert capex.tags[0].concept == "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment"
    assert cash.tags[0].member is None
    assert capex.tags[0].member is None
    assert "M1-T7" in config.period_rule
    assert "M1-T7" in cash.when_missing


def test_config_has_no_secret_or_contact_email() -> None:
    text = CONFIG_PATH.read_text(encoding="utf-8")
    assert "@" not in text
    assert "OPENAI_API_KEY" not in text
    assert "SEC_USER_AGENT" not in text
