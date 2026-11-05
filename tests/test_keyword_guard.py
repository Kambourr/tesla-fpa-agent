from __future__ import annotations

import pytest

from agent.keyword_guard import GuardHit, check_narrative, check_text

FLAGGED = [
    ("We recommend buying the stock for the rebound.", "we recommend"),
    ("Investors should sell the stock after the report.", "investors should"),
    ("Our sell rating reflects the valuation gap.", "sell rating"),
    ("Analysts see a strong buy on TSLA this year.", "strong buy"),
    ("Shares are a buy at this level.", "shares are a buy"),
    ("The stock is rated overweight on the ramp.", "overweight"),
    ("Our price target is $300 for the year.", "price target"),
    ("Target price of $300 for the year.", "target price"),
    ("Fair value is $280 per share.", "fair value"),
    ("TSLA shares are worth $250 today.", "tsla shares are worth"),
    ("The upside of 25% from here is clear.", "upside of 25%"),
    ("Expect a downside of $40 for the stock.", "downside of $40"),
    ("The stock price should reach $250 next year.", "stock price should"),
    ("Tesla looks undervalued after the drop.", "undervalued"),
    ("Buy shares before the report.", "buy shares"),
    ("Rate it outperform for now.", "outperform"),
    ("Investors should accumulate on weakness.", "accumulate"),
]

CLEAN = [
    "Automotive sales revenue was $20.1 billion, below the forecast.",
    "Deliveries sold were 497,099 units.",
    "Gross margin rose 1.2 percentage points year over year.",
    "Operating expenses were unfavorable to the forecast by $0.3 billion.",
    "Sales of regulatory credits declined as expected.",
    "Energy storage deployments reached 9.6 GWh in the quarter.",
    "Revenue per vehicle increased on a richer model mix.",
    "Diluted earnings per share was $0.52, below the forecast of $0.61 per share.",
    "Tesla repurchased shares at an average of $250 per share.",
    "Customers buy vehicles from the company's showrooms.",
    "Tesla will buy back shares under its program.",
    "Sell-through of inventory slowed in the quarter.",
    "The accumulated depreciation balance increased.",
    "The fair value of regulatory credits was $1.2 billion.",
    "Downside of 8% to operating income in the bear case.",
    "Vehicles sold in the quarter rose 5 percent versus the forecast.",
]


@pytest.mark.parametrize(("text", "expected"), FLAGGED)
def test_flags_buy_sell_and_price_target_language(text: str, expected: str) -> None:
    phrases = [hit.phrase.lower() for hit in check_text(text, "memo")]
    assert any(expected in phrase for phrase in phrases), phrases


@pytest.mark.parametrize("text", CLEAN)
def test_passes_variance_language(text: str) -> None:
    assert check_text(text, "memo") == ()


def test_hit_positions_match_the_source_text() -> None:
    text = "Growth was strong. Our price target is $300."
    (hit,) = check_text(text, "memo")
    assert hit == GuardHit(
        phrase="price target",
        start=text.index("price target"),
        end=text.index("price target") + len("price target"),
        text_kind="memo",
    )
    assert text[hit.start : hit.end] == hit.phrase


def test_check_narrative_reports_text_kind_and_positions() -> None:
    memo = "Automotive revenue was $20.1 billion. We recommend buying the stock."
    answers = {
        1: "Deliveries rose 5 percent.",
        3: "Our price target is $300.",
    }

    hits = check_narrative(memo, answers)

    assert [hit.text_kind for hit in hits] == ["memo", "memo", "answer 3"]
    assert hits[0].phrase == "We recommend"
    assert hits[0].start == memo.index("We recommend")
    assert hits[1].phrase == "buying the stock"
    assert hits[2].phrase == "price target"
    sources = {"memo": memo, "answer 3": answers[3]}
    for hit in hits:
        assert sources[hit.text_kind][hit.start : hit.end] == hit.phrase


def test_check_narrative_is_empty_for_a_clean_memo_and_answers() -> None:
    memo = "Gross margin rose 1.2 percentage points. Operating expenses were unfavorable."
    answers = {1: "Sales of regulatory credits declined.", 2: "Revenue per vehicle rose."}

    assert check_narrative(memo, answers) == ()


def test_eps_earlier_in_a_sentence_does_not_hide_a_price_target() -> None:
    text = "EPS was $0.52 per share and the target is $300 per share."
    hits = check_text(text, "memo")
    assert [hit.phrase for hit in hits] == ["$300 per share"]
