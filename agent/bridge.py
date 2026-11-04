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
