"""Token and cost logging. Fake results only: no network and no real key."""

import io
from types import SimpleNamespace

import pytest

from agent.usage import (
    RunUsage,
    estimate_cost,
    format_usage,
    load_prices,
    log_usage,
    summarize_usage,
)

FAKE_KEY = "FAKE-OPENAI-KEY-VALUE-123"
FAKE_AGENT = "fake-agent contact@example.invalid"


def result(input_tokens: int, output_tokens: int, cached: bool | None = None) -> SimpleNamespace:
    fields = {"input_tokens": input_tokens, "output_tokens": output_tokens}
    if cached is not None:
        fields["cached"] = cached
    return SimpleNamespace(**fields)


def test_luna_cost_uses_per_million_prices() -> None:
    assert estimate_cost("gpt-6-luna", 1_000_000, 0) == pytest.approx(0.10)
    assert estimate_cost("gpt-6-luna", 0, 1_000_000) == pytest.approx(0.50)
    assert estimate_cost("gpt-6-luna", 41_200, 9_800) == pytest.approx(0.00902)


def test_astra_cost_uses_per_million_prices() -> None:
    assert estimate_cost("gpt-6-astra", 1_000_000, 0) == pytest.approx(10.0)
    assert estimate_cost("gpt-6-astra", 0, 1_000_000) == pytest.approx(50.0)
    assert estimate_cost("gpt-6-astra", 100_000, 20_000) == pytest.approx(2.0)


def test_unknown_model_has_no_estimate() -> None:
    assert estimate_cost("gpt-not-priced", 1_000, 1_000) is None


def test_cost_rounds_to_six_decimals_and_accepts_a_price_table() -> None:
    prices = {"custom": {"input": 0.3333333, "output": 0.0}}
    assert estimate_cost("custom", 1_000_000, 0, prices=prices) == 0.333333
    assert estimate_cost("custom", 1_000_000, 0, prices={}) is None


def test_price_file_lists_both_models_with_source() -> None:
    prices = load_prices()
    assert prices["gpt-6-luna"]["input"] == 0.10
    assert prices["gpt-6-astra"]["output"] == 50.0
    for model in ("gpt-6-luna", "gpt-6-astra"):
        assert prices[model]["source"].startswith("https://")


def test_summarize_sums_tokens_and_counts_cached_results() -> None:
    results = [
        result(10_000, 2_000, cached=False),
        result(20_000, 3_000, cached=False),
        result(0, 0, cached=True),
        result(5_000, 1_000, cached=False),
    ]
    usage = summarize_usage(results, "gpt-6-luna")
    assert usage.input_tokens == 35_000
    assert usage.output_tokens == 6_000
    assert usage.calls == 3
    assert usage.cached == 1
    assert usage.model == "gpt-6-luna"
    assert usage.estimated_cost_usd == estimate_cost("gpt-6-luna", 35_000, 6_000)


def test_results_without_cached_field_count_as_calls() -> None:
    usage = summarize_usage([result(100, 10), result(200, 20)], "gpt-6-astra")
    assert usage.calls == 2
    assert usage.cached == 0


def test_empty_run_is_zero_and_priced() -> None:
    usage = summarize_usage([], "gpt-6-luna")
    assert usage == RunUsage("gpt-6-luna", 0, 0, 0, 0, 0.0)


def test_format_line_has_thousands_separators_and_cost() -> None:
    usage = RunUsage("gpt-6-luna", 41_200, 9_800, 12, 0, 0.009)
    assert format_usage(usage) == (
        "narration used 12 calls (0 cached), 41,200 input and 9,800 output tokens "
        "on gpt-6-luna, estimated $0.0090"
    )


def test_format_unknown_model_says_cost_unknown() -> None:
    usage = RunUsage("gpt-not-priced", 1_000, 500, 1, 0, None)
    line = format_usage(usage)
    assert line.endswith("estimated cost unknown for gpt-not-priced")
    assert "$" not in line


def test_format_warns_only_above_one_dollar() -> None:
    over = RunUsage("gpt-6-astra", 200_000, 0, 4, 0, 2.0)
    at_target = RunUsage("gpt-6-astra", 100_000, 0, 4, 0, 1.0)
    assert "above the one-dollar target" in format_usage(over)
    assert "above the one-dollar target" not in format_usage(at_target)


def test_log_usage_writes_the_formatted_line() -> None:
    usage = RunUsage("gpt-6-luna", 41_200, 9_800, 12, 0, 0.009)
    buffer = io.StringIO()
    log_usage(usage, stream=buffer)
    assert buffer.getvalue() == format_usage(usage) + "\n"


def test_log_usage_defaults_to_current_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    usage = RunUsage("gpt-6-luna", 1, 1, 1, 0, 0.0)
    log_usage(usage)
    assert capsys.readouterr().out == format_usage(usage) + "\n"


def test_output_never_contains_secret_values(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", FAKE_KEY)
    monkeypatch.setenv("SEC_USER_AGENT", FAKE_AGENT)
    usage = summarize_usage([result(41_200, 9_800, cached=False)], "gpt-6-luna")
    unknown = RunUsage("gpt-not-priced", 1, 1, 1, 0, None)
    buffer = io.StringIO()
    for item in (usage, unknown):
        log_usage(item, stream=buffer)
    log_usage(usage)
    printed = buffer.getvalue() + capsys.readouterr().out
    assert printed
    for secret in (FAKE_KEY, FAKE_AGENT):
        assert secret not in printed
        assert secret not in format_usage(unknown)
