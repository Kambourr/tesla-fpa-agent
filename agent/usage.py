"""Token counts and estimated cost for one narration run.

Prices come from ``config/model_prices.json``, in USD per million tokens. The
log line never includes an environment value: it names the model and the
counts only. Callers keep ``OPENAI_API_KEY`` and ``SEC_USER_AGENT`` out of it.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

PRICES_PATH = Path(__file__).resolve().parents[1] / "config" / "model_prices.json"
ONE_DOLLAR_TARGET = 1.00
TOKENS_PER_PRICE_UNIT = 1_000_000


@dataclass(frozen=True)
class RunUsage:
    """Totals for one run. ``estimated_cost_usd`` is None for an unpriced model."""

    model: str
    input_tokens: int
    output_tokens: int
    calls: int
    cached: int
    estimated_cost_usd: float | None


def load_prices(path: Path = PRICES_PATH) -> dict[str, dict[str, Any]]:
    """Read the price table: model name to USD per million input and output tokens."""
    return json.loads(path.read_text(encoding="utf-8"))


def estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    prices: Mapping[str, Mapping[str, Any]] | None = None,
) -> float | None:
    """Estimated USD for the tokens, rounded to 6 decimals. None for an unknown model."""
    table = load_prices() if prices is None else prices
    entry = table.get(model)
    if entry is None:
        return None
    dollars = (
        input_tokens * float(entry["input"]) + output_tokens * float(entry["output"])
    ) / TOKENS_PER_PRICE_UNIT
    return round(dollars, 6)


def summarize_usage(results: Iterable[Any], model: str) -> RunUsage:
    """Sum the token counts of a run's results.

    A result counts as a call unless its ``cached`` attribute is true. A result
    without that attribute counts as a call, because the field is added in
    parallel and older results do not carry it.
    """
    items = list(results)
    cached = sum(1 for item in items if getattr(item, "cached", False))
    input_tokens = sum(int(item.input_tokens) for item in items)
    output_tokens = sum(int(item.output_tokens) for item in items)
    return RunUsage(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        calls=len(items) - cached,
        cached=cached,
        estimated_cost_usd=estimate_cost(model, input_tokens, output_tokens),
    )


def format_usage(usage: RunUsage) -> str:
    """One log line, for example: narration used 12 calls (0 cached), ..."""
    line = (
        f"narration used {usage.calls} calls ({usage.cached} cached), "
        f"{usage.input_tokens:,} input and {usage.output_tokens:,} output tokens"
    )
    if usage.estimated_cost_usd is None:
        return f"{line}; estimated cost unknown for {usage.model}"
    line += f" on {usage.model}, estimated ${usage.estimated_cost_usd:.4f}"
    if usage.estimated_cost_usd > ONE_DOLLAR_TARGET:
        line += " (above the one-dollar target)"
    return line


def log_usage(usage: RunUsage, stream: TextIO | None = None) -> None:
    """Print the usage line. ``None`` means the current ``sys.stdout``."""
    print(format_usage(usage), file=stream if stream is not None else sys.stdout)
