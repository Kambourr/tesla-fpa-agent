"""Segment facts read from a filing's XBRL instance. Nothing here calls the network."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest
from tests.test_ingest import _block_network, write_filings

from agent.actuals import ReportedFact
from agent.deliveries import default_csv_path
from agent.ingest import run_ingest
from agent.instances import facts_from_instance, instance_name
from agent.sec import SecClient
from agent.xbrl_map import load_xbrl_map

ACCESSION = "0001628280-26-066775"
SALES = "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"

INSTANCE = """<?xml version="1.0" encoding="utf-8"?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"
  xmlns:xbrldi="http://xbrl.org/2006/xbrldi"
  xmlns:us-gaap="http://fasb.org/us-gaap/2026"
  xmlns:tsla="http://www.tesla.com/20260930"
  xmlns:srt="http://fasb.org/srt/2026"
  xmlns:iso4217="http://www.xbrl.org/2003/iso4217">
  <xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>
  <xbrli:unit id="eur"><xbrli:measure>iso4217:EUR</xbrli:measure></xbrli:unit>
  <xbrli:context id="q3-26-other-axis">
    <xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0001318605</xbrli:identifier>
      <xbrli:segment><xbrldi:explicitMember dimension="us-gaap:StatementBusinessSegmentsAxis">tsla:EnergyGenerationAndStorageMember</xbrldi:explicitMember></xbrli:segment>
    </xbrli:entity>
    <xbrli:period><xbrli:startDate>2026-07-01</xbrli:startDate><xbrli:endDate>2026-09-30</xbrli:endDate></xbrli:period>
  </xbrli:context>
  <xbrli:context id="q3-26-sales">
    <xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0001318605</xbrli:identifier>
      <xbrli:segment><xbrldi:explicitMember dimension="srt:ProductOrServiceAxis">tsla:AutomotiveSalesMember</xbrldi:explicitMember></xbrli:segment>
    </xbrli:entity>
    <xbrli:period><xbrli:startDate>2026-07-01</xbrli:startDate><xbrli:endDate>2026-09-30</xbrli:endDate></xbrli:period>
  </xbrli:context>
  <xbrli:context id="q3-26-credits">
    <xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0001318605</xbrli:identifier>
      <xbrli:segment><xbrldi:explicitMember dimension="srt:ProductOrServiceAxis">tsla:AutomotiveRegulatoryCreditsMember</xbrldi:explicitMember></xbrli:segment>
    </xbrli:entity>
    <xbrli:period><xbrli:startDate>2026-07-01</xbrli:startDate><xbrli:endDate>2026-09-30</xbrli:endDate></xbrli:period>
  </xbrli:context>
  <xbrli:context id="q3-26-leasing">
    <xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0001318605</xbrli:identifier>
      <xbrli:segment><xbrldi:explicitMember dimension="srt:ProductOrServiceAxis">tsla:AutomotiveLeasingMember</xbrldi:explicitMember></xbrli:segment>
    </xbrli:entity>
    <xbrli:period><xbrli:startDate>2026-07-01</xbrli:startDate><xbrli:endDate>2026-09-30</xbrli:endDate></xbrli:period>
  </xbrli:context>
  <xbrli:context id="q3-26-energy">
    <xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0001318605</xbrli:identifier>
      <xbrli:segment><xbrldi:explicitMember dimension="srt:ProductOrServiceAxis">tsla:EnergyGenerationAndStorageMember</xbrldi:explicitMember></xbrli:segment>
    </xbrli:entity>
    <xbrli:period><xbrli:startDate>2026-07-01</xbrli:startDate><xbrli:endDate>2026-09-30</xbrli:endDate></xbrli:period>
  </xbrli:context>
  <xbrli:context id="q3-26-services">
    <xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0001318605</xbrli:identifier>
      <xbrli:segment><xbrldi:explicitMember dimension="srt:ProductOrServiceAxis">tsla:ServicesAndOtherMember</xbrldi:explicitMember></xbrli:segment>
    </xbrli:entity>
    <xbrli:period><xbrli:startDate>2026-07-01</xbrli:startDate><xbrli:endDate>2026-09-30</xbrli:endDate></xbrli:period>
  </xbrli:context>
  <xbrli:context id="q3-26-total">
    <xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0001318605</xbrli:identifier></xbrli:entity>
    <xbrli:period><xbrli:startDate>2026-07-01</xbrli:startDate><xbrli:endDate>2026-09-30</xbrli:endDate></xbrli:period>
  </xbrli:context>
  <xbrli:context id="q3-26-two-dims">
    <xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0001318605</xbrli:identifier>
      <xbrli:segment>
        <xbrldi:explicitMember dimension="srt:ProductOrServiceAxis">tsla:AutomotiveSalesMember</xbrldi:explicitMember>
        <xbrldi:explicitMember dimension="us-gaap:StatementBusinessSegmentsAxis">tsla:AutomotiveSegmentMember</xbrldi:explicitMember>
      </xbrli:segment>
    </xbrli:entity>
    <xbrli:period><xbrli:startDate>2026-07-01</xbrli:startDate><xbrli:endDate>2026-09-30</xbrli:endDate></xbrli:period>
  </xbrli:context>
  <xbrli:context id="q3-26-cost-automotive">
    <xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0001318605</xbrli:identifier>
      <xbrli:segment><xbrldi:explicitMember dimension="srt:ProductOrServiceAxis">tsla:AutomotiveRevenuesMember</xbrldi:explicitMember></xbrli:segment>
    </xbrli:entity>
    <xbrli:period><xbrli:startDate>2026-07-01</xbrli:startDate><xbrli:endDate>2026-09-30</xbrli:endDate></xbrli:period>
  </xbrli:context>
  <xbrli:context id="q3-26-cost-sales">
    <xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0001318605</xbrli:identifier>
      <xbrli:segment><xbrldi:explicitMember dimension="srt:ProductOrServiceAxis">tsla:AutomotiveSalesMember</xbrldi:explicitMember></xbrli:segment>
    </xbrli:entity>
    <xbrli:period><xbrli:startDate>2026-07-01</xbrli:startDate><xbrli:endDate>2026-09-30</xbrli:endDate></xbrli:period>
  </xbrli:context>
  <xbrli:context id="q3-26-cost-leasing">
    <xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0001318605</xbrli:identifier>
      <xbrli:segment><xbrldi:explicitMember dimension="srt:ProductOrServiceAxis">tsla:AutomotiveLeasingMember</xbrldi:explicitMember></xbrli:segment>
    </xbrli:entity>
    <xbrli:period><xbrli:startDate>2026-07-01</xbrli:startDate><xbrli:endDate>2026-09-30</xbrli:endDate></xbrli:period>
  </xbrli:context>
  <xbrli:context id="q3-26-cost-energy">
    <xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0001318605</xbrli:identifier>
      <xbrli:segment><xbrldi:explicitMember dimension="srt:ProductOrServiceAxis">tsla:EnergyGenerationAndStorageMember</xbrldi:explicitMember></xbrli:segment>
    </xbrli:entity>
    <xbrli:period><xbrli:startDate>2026-07-01</xbrli:startDate><xbrli:endDate>2026-09-30</xbrli:endDate></xbrli:period>
  </xbrli:context>
  <xbrli:context id="q3-26-cost-services">
    <xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0001318605</xbrli:identifier>
      <xbrli:segment><xbrldi:explicitMember dimension="srt:ProductOrServiceAxis">tsla:ServicesAndOtherMember</xbrldi:explicitMember></xbrli:segment>
    </xbrli:entity>
    <xbrli:period><xbrli:startDate>2026-07-01</xbrli:startDate><xbrli:endDate>2026-09-30</xbrli:endDate></xbrli:period>
  </xbrli:context>
  <xbrli:context id="ytd-26-sales">
    <xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0001318605</xbrli:identifier>
      <xbrli:segment><xbrldi:explicitMember dimension="srt:ProductOrServiceAxis">tsla:AutomotiveSalesMember</xbrldi:explicitMember></xbrli:segment>
    </xbrli:entity>
    <xbrli:period><xbrli:startDate>2026-01-01</xbrli:startDate><xbrli:endDate>2026-09-30</xbrli:endDate></xbrli:period>
  </xbrli:context>
  <xbrli:context id="q3-25-sales">
    <xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0001318605</xbrli:identifier>
      <xbrli:segment><xbrldi:explicitMember dimension="srt:ProductOrServiceAxis">tsla:AutomotiveSalesMember</xbrldi:explicitMember></xbrli:segment>
    </xbrli:entity>
    <xbrli:period><xbrli:startDate>2025-07-01</xbrli:startDate><xbrli:endDate>2025-09-30</xbrli:endDate></xbrli:period>
  </xbrli:context>
  <xbrli:context id="q3-25-cost-automotive">
    <xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0001318605</xbrli:identifier>
      <xbrli:segment><xbrldi:explicitMember dimension="srt:ProductOrServiceAxis">tsla:AutomotiveRevenuesMember</xbrldi:explicitMember></xbrli:segment>
    </xbrli:entity>
    <xbrli:period><xbrli:startDate>2025-07-01</xbrli:startDate><xbrli:endDate>2025-09-30</xbrli:endDate></xbrli:period>
  </xbrli:context>
  <xbrli:context id="q3-25-services-eur">
    <xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0001318605</xbrli:identifier>
      <xbrli:segment><xbrldi:explicitMember dimension="srt:ProductOrServiceAxis">tsla:ServicesAndOtherMember</xbrldi:explicitMember></xbrli:segment>
    </xbrli:entity>
    <xbrli:period><xbrli:startDate>2025-07-01</xbrli:startDate><xbrli:endDate>2025-09-30</xbrli:endDate></xbrli:period>
  </xbrli:context>
  <xbrli:context id="instant-26-sales">
    <xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0001318605</xbrli:identifier>
      <xbrli:segment><xbrldi:explicitMember dimension="srt:ProductOrServiceAxis">tsla:AutomotiveSalesMember</xbrldi:explicitMember></xbrli:segment>
    </xbrli:entity>
    <xbrli:period><xbrli:instant>2026-09-30</xbrli:instant></xbrli:period>
  </xbrli:context>
  <us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax contextRef="q3-26-other-axis" unitRef="usd" decimals="-6">1000000</us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax>
  <us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax contextRef="q3-26-sales" unitRef="usd" decimals="-6">20094000000</us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax>
  <us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax contextRef="q3-26-sales" unitRef="usd" decimals="-6">20094000000</us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax>
  <us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax contextRef="q3-26-credits" unitRef="usd" decimals="-6">113000000</us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax>
  <us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax contextRef="q3-26-leasing" unitRef="usd" decimals="-6">353000000</us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax>
  <us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax contextRef="q3-26-energy" unitRef="usd" decimals="-7">2880000000</us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax>
  <us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax contextRef="q3-26-energy" unitRef="usd" decimals="-6">2881000000</us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax>
  <us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax contextRef="q3-26-services" unitRef="usd" decimals="-6">4605000000</us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax>
  <us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax contextRef="q3-26-two-dims" unitRef="usd" decimals="-6">999000000</us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax>
  <us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax contextRef="ytd-26-sales" unitRef="usd" decimals="-6">59000000000</us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax>
  <us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax contextRef="q3-25-sales" unitRef="usd" decimals="-6">17000000000</us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax>
  <us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax contextRef="q3-25-services-eur" unitRef="eur" decimals="-6">5000000</us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax>
  <us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax contextRef="instant-26-sales" unitRef="usd" decimals="-6">7000000</us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax>
  <us-gaap:Revenues contextRef="q3-26-total" unitRef="usd" decimals="-6">28046000000</us-gaap:Revenues>
  <us-gaap:CostOfRevenue contextRef="q3-26-cost-automotive" unitRef="usd" decimals="-6">16754000000</us-gaap:CostOfRevenue>
  <us-gaap:CostOfRevenue contextRef="q3-26-cost-sales" unitRef="usd" decimals="-6">15000000000</us-gaap:CostOfRevenue>
  <us-gaap:CostOfRevenue contextRef="q3-26-cost-leasing" unitRef="usd" decimals="-6">1754000000</us-gaap:CostOfRevenue>
  <us-gaap:CostOfRevenue contextRef="q3-26-cost-energy" unitRef="usd" decimals="-6">1927000000</us-gaap:CostOfRevenue>
  <us-gaap:CostOfRevenue contextRef="q3-26-cost-services" unitRef="usd" decimals="-6">3871000000</us-gaap:CostOfRevenue>
  <us-gaap:CostOfRevenue contextRef="q3-25-cost-automotive" unitRef="usd" decimals="-6">1700000000</us-gaap:CostOfRevenue>
  <tsla:AutomotiveCostOfRevenues contextRef="q3-25-cost-automotive" unitRef="usd" decimals="-6">1500000000</tsla:AutomotiveCostOfRevenues>
</xbrli:xbrl>
"""  # noqa: E501


def _rows(facts: list[ReportedFact]) -> set[tuple[object, ...]]:
    return {
        (
            fact.metric,
            fact.member,
            fact.period_start,
            fact.period_end,
            fact.value,
            fact.concept,
            fact.unit,
        )
        for fact in facts
    }


def _read_instance(xml: str = INSTANCE) -> list[ReportedFact]:
    return facts_from_instance(
        xml.encode("utf-8"),
        accession=ACCESSION,
        form="10-Q",
        filing_period_end=date(2026, 9, 30),
        filing_date=date(2026, 10, 21),
        filing_url="https://www.sec.gov/Archives/edgar/data/1318605/000162828026066775/tsla.htm",
        tag_map=load_xbrl_map(),
    )


def test_instance_yields_each_segment_line_for_each_duration() -> None:
    rows = _rows(_read_instance())
    q3 = (date(2026, 7, 1), date(2026, 9, 30))
    q3_prior = (date(2025, 7, 1), date(2025, 9, 30))
    ytd = (date(2026, 1, 1), date(2026, 9, 30))
    expected = {
        ("automotive_sales", "tsla:AutomotiveSalesMember", *q3, Decimal(20094000000), SALES, "USD"),
        (
            "automotive_regulatory_credits",
            "tsla:AutomotiveRegulatoryCreditsMember",
            *q3,
            Decimal(113000000),
            SALES,
            "USD",
        ),
        (
            "automotive_leasing",
            "tsla:AutomotiveLeasingMember",
            *q3,
            Decimal(353000000),
            SALES,
            "USD",
        ),
        (
            "energy_generation_and_storage",
            "tsla:EnergyGenerationAndStorageMember",
            *q3,
            Decimal(2881000000),
            SALES,
            "USD",
        ),
        (
            "services_and_other",
            "tsla:ServicesAndOtherMember",
            *q3,
            Decimal(4605000000),
            SALES,
            "USD",
        ),
        (
            "cost_of_revenue_automotive",
            "tsla:AutomotiveRevenuesMember",
            *q3,
            Decimal(16754000000),
            "us-gaap:CostOfRevenue",
            "USD",
        ),
        (
            "cost_of_revenue_automotive_sales",
            "tsla:AutomotiveSalesMember",
            *q3,
            Decimal(15000000000),
            "us-gaap:CostOfRevenue",
            "USD",
        ),
        (
            "cost_of_revenue_automotive_leasing",
            "tsla:AutomotiveLeasingMember",
            *q3,
            Decimal(1754000000),
            "us-gaap:CostOfRevenue",
            "USD",
        ),
        (
            "cost_of_revenue_energy",
            "tsla:EnergyGenerationAndStorageMember",
            *q3,
            Decimal(1927000000),
            "us-gaap:CostOfRevenue",
            "USD",
        ),
        (
            "cost_of_revenue_services",
            "tsla:ServicesAndOtherMember",
            *q3,
            Decimal(3871000000),
            "us-gaap:CostOfRevenue",
            "USD",
        ),
        (
            "automotive_sales",
            "tsla:AutomotiveSalesMember",
            *q3_prior,
            Decimal(17000000000),
            SALES,
            "USD",
        ),
        (
            "cost_of_revenue_automotive",
            "tsla:AutomotiveRevenuesMember",
            *q3_prior,
            Decimal(1500000000),
            "tsla:AutomotiveCostOfRevenues",
            "USD",
        ),
        (
            "automotive_sales",
            "tsla:AutomotiveSalesMember",
            *ytd,
            Decimal(59000000000),
            SALES,
            "USD",
        ),
    }
    assert rows == expected


def test_instance_ignores_other_axes_multi_dimension_instant_and_other_units() -> None:
    facts = _read_instance()
    values = [fact.value for fact in facts]
    # 1,000,000 (other axis), 999,000,000 (two dimensions), 7,000,000 (instant),
    # 5,000,000 (EUR), and 28,046,000,000 (no dimension) must not appear.
    for ignored in (1000000, 999000000, 7000000, 5000000, 28046000000):
        assert Decimal(ignored) not in values
    assert not any(fact.metric == "total_revenue" for fact in facts)


def test_rounded_copy_of_a_fact_loses_to_the_precise_copy() -> None:
    """The rounded energy copy comes first in the document and must not win."""
    energy = [
        fact.value
        for fact in _read_instance()
        if fact.metric == "energy_generation_and_storage" and fact.period_start == date(2026, 7, 1)
    ]
    assert energy == [Decimal(2881000000)]


def test_two_conflicting_facts_at_the_same_precision_fail() -> None:
    xml = INSTANCE.replace(
        'contextRef="q3-26-sales" unitRef="usd" decimals="-6">20094000000',
        'contextRef="q3-26-sales" unitRef="usd" decimals="-6">20000000000',
        1,
    )
    with pytest.raises(ValueError, match="two values"):
        _read_instance(xml)


def test_repeated_fact_is_stored_once() -> None:
    facts = _read_instance()
    sales_q3 = [
        fact
        for fact in facts
        if fact.metric == "automotive_sales"
        and fact.period_end == date(2026, 9, 30)
        and fact.period_start == date(2026, 7, 1)
    ]
    assert len(sales_q3) == 1


def test_instance_fact_carries_the_filing_it_came_from() -> None:
    facts = _read_instance()
    assert facts
    for fact in facts:
        assert fact.accession == ACCESSION
        assert fact.form == "10-Q"
        assert fact.filing_period_end == date(2026, 9, 30)
        assert fact.filing_date == date(2026, 10, 21)
        assert fact.filing_url.endswith("/000162828026066775/tsla.htm")


def test_first_tag_in_config_order_wins_when_the_earlier_tag_is_present() -> None:
    """2025-Q3 has both the tsla cost tag and CostOfRevenue. The config lists tsla first."""
    facts = _read_instance()
    cost = [
        fact
        for fact in facts
        if fact.metric == "cost_of_revenue_automotive" and fact.period_start == date(2025, 7, 1)
    ]
    assert [(fact.concept, fact.value) for fact in cost] == [
        ("tsla:AutomotiveCostOfRevenues", Decimal(1500000000))
    ]


def test_instance_name_prefers_the_inline_htm_instance() -> None:
    listing = {
        "directory": {
            "item": [
                {"name": "FilingSummary.xml"},
                {"name": "R1.htm"},
                {"name": "tsla-20260930.xml"},
                {"name": "tsla-20260930_htm.xml"},
                {"name": "tsla-20260930_cal.xml"},
            ]
        }
    }
    assert instance_name(json.dumps(listing).encode("utf-8")) == "tsla-20260930_htm.xml"


def test_instance_name_falls_back_to_a_plain_xml_that_is_not_a_linkbase() -> None:
    listing = {
        "directory": {
            "item": [
                {"name": "FilingSummary.xml"},
                {"name": "tsla-20260930_cal.xml"},
                {"name": "tsla-20260930_def.xml"},
                {"name": "tsla-20260930_lab.xml"},
                {"name": "tsla-20260930_pre.xml"},
                {"name": "tsla-20260930.xml"},
            ]
        }
    }
    assert instance_name(json.dumps(listing).encode("utf-8")) == "tsla-20260930.xml"


def test_instance_name_fails_when_no_instance_is_listed() -> None:
    listing = {"directory": {"item": [{"name": "FilingSummary.xml"}, {"name": "R1.htm"}]}}
    with pytest.raises(ValueError, match="no XBRL instance"):
        instance_name(json.dumps(listing).encode("utf-8"))


def _client(tmp_path: Path, seen: list[str]) -> SecClient:
    def transport(url: str, user_agent: str) -> bytes:
        seen.append(url)
        return b"{}"

    return SecClient(
        "fixture-contact-string",
        cache_dir=tmp_path / "cache",
        transport=transport,
        now_ns=lambda: 0,
        sleep_ns=lambda _ns: None,
    )


def test_filing_urls_are_built_from_a_dashed_accession(tmp_path: Path) -> None:
    seen: list[str] = []
    client = _client(tmp_path, seen)
    client.filing_folder_index(ACCESSION)
    client.filing_document(ACCESSION, "tsla-20260930_htm.xml")
    assert seen == [
        "https://www.sec.gov/Archives/edgar/data/1318605/000162828026066775/index.json",
        "https://www.sec.gov/Archives/edgar/data/1318605/000162828026066775/tsla-20260930_htm.xml",
    ]


@pytest.mark.parametrize(
    "accession",
    ["000162828026066775", "0001628280-26-06677", "0001628280-26-066775/../x", "../etc"],
)
def test_sec_client_rejects_a_bad_accession(tmp_path: Path, accession: str) -> None:
    seen: list[str] = []
    client = _client(tmp_path, seen)
    with pytest.raises(ValueError, match="accession"):
        client.filing_folder_index(accession)
    with pytest.raises(ValueError, match="accession"):
        client.filing_document(accession, "tsla_htm.xml")
    assert seen == []


@pytest.mark.parametrize("name", ["", "../secret.xml", "a/b.xml", "a b.xml", "x%2F.xml"])
def test_sec_client_rejects_a_bad_file_name(tmp_path: Path, name: str) -> None:
    seen: list[str] = []
    client = _client(tmp_path, seen)
    with pytest.raises(ValueError, match="file name"):
        client.filing_document(ACCESSION, name)
    assert seen == []


def test_fixture_ingest_reads_the_instances_folder_into_fact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _block_network(monkeypatch)
    fixtures = tmp_path / "sec"
    write_filings(fixtures)
    submissions = json.loads((fixtures / "submissions.json").read_text(encoding="utf-8"))
    recent = submissions["filings"]["recent"]
    accession = next(
        recent["accessionNumber"][index]
        for index, report in enumerate(recent["reportDate"])
        if report == "2026-09-30"
    )
    instances = fixtures / "instances"
    instances.mkdir()
    (instances / f"{accession}.xml").write_text(INSTANCE, encoding="utf-8")
    database = tmp_path / "fpa.duckdb"
    run_ingest(database=database, csv_path=default_csv_path(), fixtures=fixtures)

    connection = duckdb.connect(str(database), read_only=True)
    try:
        stored = connection.execute(
            """
            SELECT value, accession, member FROM fact
            WHERE metric = 'automotive_sales'
              AND period_start = DATE '2026-07-01' AND period_end = DATE '2026-09-30'
            """
        ).fetchall()
        actual = connection.execute(
            """
            SELECT value, basis FROM quarter_actual
            WHERE quarter = '2026-Q3' AND metric = 'automotive_sales'
            """
        ).fetchone()
    finally:
        connection.close()
    assert stored == [(Decimal(20094000000), accession, "tsla:AutomotiveSalesMember")]
    assert actual is not None
    assert int(actual[0]) == 20094000000
    assert actual[1] == "first_reported"


def test_fixture_ingest_without_instances_folder_stores_no_segment_lines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _block_network(monkeypatch)
    fixtures = tmp_path / "sec"
    write_filings(fixtures)
    database = tmp_path / "fpa.duckdb"
    run_ingest(database=database, csv_path=default_csv_path(), fixtures=fixtures)
    connection = duckdb.connect(str(database), read_only=True)
    try:
        count = connection.execute(
            "SELECT count(*) FROM fact WHERE metric = 'automotive_sales'"
        ).fetchone()
    finally:
        connection.close()
    assert count == (0,)
