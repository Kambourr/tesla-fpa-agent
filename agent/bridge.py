"""Shared shape for a variance bar. Each bridge module fills its own drivers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import duckdb

_PLACES = Decimal("0.0001")


class BridgeError(Exception):
    """A bridge input is missing, so the bars cannot be required to sum."""


@dataclass(frozen=True)
class BridgeBar:
    """One labeled driver. ``favorable`` is true only when ``value`` is positive."""

    driver: str
    value: Decimal
    favorable: bool


def bar(driver: str, value: Decimal) -> BridgeBar:
    """Quantize a bar. Zero and negative values are not favorable."""
    amount = value.quantize(_PLACES)
    return BridgeBar(driver=driver, value=amount, favorable=amount > 0)


# Largest rounding gap a bridge may absorb. Quantizing each bar to four places,
# and forecast lines that were each quantized before they were multiplied,
# leave gaps of cents. A gap above this means the inputs do not tie, for
# example segment costs that do not add up to total cost.
MAX_ROUNDING_GAP = Decimal("1000")


def reconciled(
    raw: tuple[tuple[str, Decimal], ...],
    variance: Decimal,
) -> tuple[BridgeBar, ...]:
    """Quantize the bars and make them sum exactly to ``variance``.

    The rounding gap goes to the bar with the largest absolute amount, the
    first such bar on a tie, where it is the smallest share of the bar.
    """
    if not raw:
        raise BridgeError("a bridge needs at least one bar")
    target = variance.quantize(_PLACES)
    amounts = [value.quantize(_PLACES) for _, value in raw]
    gap = target - sum(amounts, Decimal(0))
    if abs(gap) > MAX_ROUNDING_GAP:
        raise BridgeError(f"bars miss the variance by {gap}, so the inputs do not tie")
    largest = max(range(len(amounts)), key=lambda index: abs(amounts[index]))
    amounts[largest] += gap
    return tuple(bar(driver, amount) for (driver, _), amount in zip(raw, amounts, strict=True))


def optional_amount(
    connection: duckdb.DuckDBPyConnection,
    quarter: str,
    metric: str,
    *,
    scenario: str | None,
) -> Decimal | None:
    """Like ``signed_amount``, but a missing line is ``None``."""
    try:
        return signed_amount(connection, quarter, metric, scenario=scenario)
    except BridgeError:
        return None


def replace_bridge(
    connection: duckdb.DuckDBPyConnection,
    quarter: str,
    bridge: str,
    bars: tuple[BridgeBar, ...],
) -> None:
    """Replace every bar of one bridge for one quarter."""
    connection.execute(
        "DELETE FROM bridge WHERE quarter = ? AND bridge = ?",
        [quarter, bridge],
    )
    for item in bars:
        connection.execute(
            "INSERT INTO bridge VALUES (?, ?, ?, ?, ?)",
            [quarter, bridge, item.driver, item.value, item.favorable],
        )


def signed_amount(
    connection: duckdb.DuckDBPyConnection,
    quarter: str,
    metric: str,
    *,
    scenario: str | None,
) -> Decimal:
    """Read one required amount. ``scenario`` selects the base forecast."""
    if scenario is None:
        query = "SELECT value FROM quarter_actual WHERE quarter = ? AND metric = ?"
        parameters: list[str] = [quarter, metric]
    else:
        query = """
            SELECT value FROM forecast
            WHERE quarter = ? AND metric = ? AND scenario = ?
        """
        parameters = [quarter, metric, scenario]
    found = connection.execute(query, parameters).fetchone()
    if found is None or found[0] is None:
        source = "forecast" if scenario else "quarter_actual"
        raise BridgeError(f"{source} has no {metric} for {quarter}")
    return found[0]
