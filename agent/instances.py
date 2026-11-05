"""Read segment (dimensional) facts from each filing's XBRL instance.

SEC companyfacts drops XBRL dimensions, so the revenue and cost lines by
segment are read from the instance document of each 10-Q and 10-K. A fact
counts only when its context has exactly one dimension and that dimension is
the axis and member the tag map names. The walk follows ``selection`` in
``config/xbrl_tags.json``.
"""

from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from typing import Any

from agent.actuals import ReportedFact, statement_filings
from agent.sec import SecClient
from agent.xbrl_map import XbrlMap

XBRLI = "http://www.xbrl.org/2003/instance"
XBRLDI = "http://xbrl.org/2006/xbrldi"
USD_MEASURE = "iso4217:USD"
# The segment history starts this many years before the latest filing.
SEGMENT_YEARS_BACK = 5
_SUPPORT_SUFFIXES = ("_cal.xml", "_def.xml", "_lab.xml", "_pre.xml")

# A context's dimensions as (axis, member) pairs. None when it has a typed
# member, which no configured tag matches.
_Dimensions = list[tuple[str, str]] | None
_Context = tuple[date, date, _Dimensions]


def instance_name(index_json: bytes) -> str:
    """Pick the XBRL instance from a filing folder's ``index.json``.

    The inline instance is the ``*_htm.xml`` file. Without one, the first
    other ``.xml`` file that is not the summary or a linkbase is used.
    """
    listing = json.loads(index_json)
    names = [item["name"] for item in listing["directory"]["item"]]
    for name in names:
        if name.endswith("_htm.xml"):
            return name
    for name in names:
        if (
            name.endswith(".xml")
            and name != "FilingSummary.xml"
            and not name.endswith(_SUPPORT_SUFFIXES)
        ):
            return name
    raise ValueError("filing folder lists no XBRL instance document")


def segment_since(submissions: dict[str, Any]) -> date:
    """Jan 1 of the latest 10-Q or 10-K report year, minus the lookback."""
    filings = statement_filings(submissions)
    if not filings:
        raise ValueError("submissions list no 10-Q or 10-K filings")
    latest = max(filing.period_end for filing in filings.values())
    return date(latest.year - SEGMENT_YEARS_BACK, 1, 1)


def segment_facts(
    client: SecClient,
    submissions: dict[str, Any],
    tag_map: XbrlMap,
    *,
    since: date,
) -> list[ReportedFact]:
    """Fetch and read the instance of each 10-Q and 10-K reported on or after ``since``."""
    facts: list[ReportedFact] = []
    for accession, filing in statement_filings(submissions).items():
        if filing.period_end < since:
            continue
        name = instance_name(client.filing_folder_index(accession))
        body = client.filing_document(accession, name)
        facts.extend(_facts_for_filing(body, accession, filing, tag_map))
    return facts


def segment_facts_from_directory(
    directory: Path,
    submissions: dict[str, Any],
    tag_map: XbrlMap,
) -> list[ReportedFact]:
    """Read ``{accession}.xml`` from ``directory`` for each matching filing. No network.

    A filing with no file in the directory is skipped.
    """
    facts: list[ReportedFact] = []
    for accession, filing in statement_filings(submissions).items():
        path = directory / f"{accession}.xml"
        if path.is_file():
            facts.extend(_facts_for_filing(path.read_bytes(), accession, filing, tag_map))
    return facts


def facts_from_instance(
    xml_bytes: bytes,
    *,
    accession: str,
    form: str,
    filing_period_end: date,
    filing_date: date,
    filing_url: str,
    tag_map: XbrlMap,
) -> list[ReportedFact]:
    """Read every dimensional series in one instance, for each duration it reports.

    For each metric and each (start, end) duration, the tags are tried in
    config order. The first tag with a USD fact whose only dimension is the
    tag's axis and member wins. Other dimensions, instant contexts and
    non-USD units are ignored. Identical repeats are deduplicated.
    """
    dimensional = [
        (metric, [tag for tag in spec.tags if tag.member is not None])
        for metric, spec in tag_map.metrics.items()
        if spec.source == "xbrl"
    ]
    dimensional = [(metric, tags) for metric, tags in dimensional if tags]
    if not dimensional:
        return []
    root, prefixes = _parse(xml_bytes)
    usd_units = _usd_unit_ids(root)
    contexts = _duration_contexts(root)
    values = _single_dimension_values(root, prefixes, usd_units, contexts, accession)
    durations = sorted({(start, end) for start, end, _ in contexts.values()})
    facts: list[ReportedFact] = []
    for metric, tags in dimensional:
        for start, end in durations:
            for tag in tags:
                found = values.get((tag.concept, start, end, tag.axis, tag.member))
                if found is None:
                    continue
                value = found[0]
                facts.append(
                    ReportedFact(
                        metric=metric,
                        period_start=start,
                        period_end=end,
                        accession=accession,
                        form=form,
                        filing_period_end=filing_period_end,
                        filing_date=filing_date,
                        filing_url=filing_url,
                        value=value,
                        unit="USD",
                        concept=tag.concept,
                        member=tag.member,
                    )
                )
                break
    return facts


def _facts_for_filing(
    body: bytes,
    accession: str,
    filing: Any,
    tag_map: XbrlMap,
) -> list[ReportedFact]:
    return facts_from_instance(
        body,
        accession=accession,
        form=filing.form,
        filing_period_end=filing.period_end,
        filing_date=filing.filing_date,
        filing_url=filing.filing_url,
        tag_map=tag_map,
    )


def _parse(xml_bytes: bytes) -> tuple[ET.Element, dict[str, list[str]]]:
    """Parse the instance and map each namespace URI to the prefixes it is declared under."""
    prefixes: dict[str, list[str]] = defaultdict(list)
    parser = ET.iterparse(BytesIO(xml_bytes), events=("start-ns",))
    for _event, (prefix, uri) in parser:
        if prefix and prefix not in prefixes[uri]:
            prefixes[uri].append(prefix)
    return parser.root, prefixes


def _usd_unit_ids(root: ET.Element) -> set[str]:
    usd: set[str] = set()
    for unit in root.findall(f"{{{XBRLI}}}unit"):
        unit_id = unit.get("id")
        measures = [(measure.text or "").strip() for measure in unit.iter(f"{{{XBRLI}}}measure")]
        if unit_id is not None and measures == [USD_MEASURE]:
            usd.add(unit_id)
    return usd


def _duration_contexts(root: ET.Element) -> dict[str, _Context]:
    """Map context id to its duration and dimensions. Instant contexts are left out."""
    contexts: dict[str, _Context] = {}
    for context in root.findall(f"{{{XBRLI}}}context"):
        context_id = context.get("id")
        period = context.find(f"{{{XBRLI}}}period")
        if context_id is None or period is None:
            continue
        start_text = period.findtext(f"{{{XBRLI}}}startDate")
        end_text = period.findtext(f"{{{XBRLI}}}endDate")
        if start_text is None or end_text is None:
            continue
        contexts[context_id] = (
            date.fromisoformat(start_text.strip()[:10]),
            date.fromisoformat(end_text.strip()[:10]),
            _dimensions(context),
        )
    return contexts


def _dimensions(context: ET.Element) -> _Dimensions:
    dimensions: list[tuple[str, str]] = []
    if next(context.iter(f"{{{XBRLDI}}}typedMember"), None) is not None:
        return None
    for member in context.iter(f"{{{XBRLDI}}}explicitMember"):
        axis = member.get("dimension")
        value = (member.text or "").strip()
        if axis is None or ":" not in axis or ":" not in value:
            return None
        dimensions.append((axis, value))
    return dimensions


def _single_dimension_values(
    root: ET.Element,
    prefixes: dict[str, list[str]],
    usd_units: set[str],
    contexts: dict[str, _Context],
    accession: str,
) -> dict[tuple[str, date, date, str, str], tuple[Decimal, float]]:
    """Map (concept, start, end, axis, member) to (value, precision) for single-dimension USD facts.

    A filing can repeat one amount at two precisions, such as 1,465,000,000 and
    a copy rounded to 1,460,000,000. The more precise copy is kept. Two copies
    at the same precision must agree.
    """
    values: dict[tuple[str, date, date, str, str], tuple[Decimal, float]] = {}
    for fact in root:
        context_ref = fact.get("contextRef")
        if context_ref is None or fact.get("unitRef") not in usd_units:
            continue
        context = contexts.get(context_ref)
        if context is None or context[2] is None or len(context[2]) != 1:
            continue
        text = (fact.text or "").strip()
        if not text:
            continue
        uri, local = _split_tag(fact.tag)
        names = [f"{prefix}:{local}" for prefix in prefixes.get(uri, [])]
        if not names:
            continue
        value = _whole_usd(text, accession)
        precision = _precision(fact.get("decimals"))
        start, end, dimensions = context
        axis, member = dimensions[0]
        for name in names:
            key = (name, start, end, axis, member)
            existing = values.get(key)
            if existing is None or precision > existing[1]:
                values[key] = (value, precision)
            elif precision == existing[1] and existing[0] != value:
                raise ValueError(f"{name} has two values for one period in {accession}")
    return values


def _precision(decimals: str | None) -> float:
    """Order duplicate facts by their ``decimals`` attribute. INF is exact; missing is lowest."""
    if decimals == "INF":
        return math.inf
    try:
        return float(int(decimals or ""))
    except ValueError:
        return -math.inf


def _split_tag(tag: str) -> tuple[str, str]:
    """Split an ElementTree ``{uri}local`` name. An unqualified name has no URI."""
    if tag.startswith("{"):
        uri, _, local = tag[1:].partition("}")
        return uri, local
    return "", tag


def _whole_usd(text: str, accession: str) -> Decimal:
    try:
        value = Decimal(text)
    except InvalidOperation as error:
        raise ValueError(f"fact value is not a number in {accession}: {text!r}") from error
    if value != value.to_integral_value():
        raise ValueError(f"fact value must be a whole dollar amount in {accession}: {text!r}")
    return value
