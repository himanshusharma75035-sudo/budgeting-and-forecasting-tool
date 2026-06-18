"""Waterfall (bridge) construction and price/volume decomposition (DESIGN.md 4.6).

A *bridge* walks from a starting value to an ending value through an ordered list of
labelled deltas (e.g. Budget -> Price -> Volume -> Actual), the staple of FP&A
waterfall charts. The price/volume decomposition splits the total change in a
``price * quantity`` figure into a price effect and a volume effect that reconcile
exactly to the total using the order-averaged (symmetric) method.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.domain.money import to_decimal


@dataclass(frozen=True)
class BridgeStep:
    """One labelled contribution to a waterfall (DESIGN.md 4.6)."""

    label: str
    delta: Decimal


@dataclass(frozen=True)
class Bridge:
    """A waterfall from ``start`` through ``steps`` to ``end`` (DESIGN.md 4.6)."""

    start: Decimal
    steps: list[BridgeStep]
    end: Decimal


def build_bridge(start: Decimal, steps: Sequence[BridgeStep]) -> Bridge:
    """Assemble a bridge whose ``end = start + sum(step.delta)`` (DESIGN.md 4.6)."""
    start = to_decimal(start)
    materialised = [BridgeStep(label=s.label, delta=to_decimal(s.delta)) for s in steps]
    end = start + sum((s.delta for s in materialised), Decimal("0"))
    return Bridge(start=start, steps=materialised, end=end)


def price_volume_decomposition(
    budget_price: Decimal,
    actual_price: Decimal,
    budget_qty: Decimal,
    actual_qty: Decimal,
) -> tuple[Decimal, Decimal]:
    """Split a price*qty change into price and volume effects (DESIGN.md 4.6).

    ORDER-AVERAGED (symmetric / Marshall-Edgeworth) method, which reconciles exactly:

        ``price_effect  = (AP - BP) * (BQ + AQ) / 2``
        ``volume_effect = (AQ - BQ) * (BP + AP) / 2``

    Their sum equals ``actual_price * actual_qty - budget_price * budget_qty`` exactly,
    avoiding the arbitrary residual / interaction term of the sequential method.

    Returns:
        ``(price_effect, volume_effect)``.
    """
    bp = to_decimal(budget_price)
    ap = to_decimal(actual_price)
    bq = to_decimal(budget_qty)
    aq = to_decimal(actual_qty)
    two = Decimal("2")
    price_effect = (ap - bp) * (bq + aq) / two
    volume_effect = (aq - bq) * (bp + ap) / two
    return price_effect, volume_effect
