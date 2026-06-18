"""Sales price / volume / mix / quantity variances (DESIGN.md 4.5).

These use the **Horngren** contribution-margin formulation of the mix and quantity
variances (deliberately NOT the AccountingTools weighted-average-CM variant). All
variances are expressed in contribution-margin currency; a positive value means actual
contribution exceeded budget (favorable) since these are margin/revenue-side measures.

Notation: AP/BP actual/budgeted price, AU/BU actual/budgeted units,
BCM budgeted contribution margin per unit.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.domain.money import to_decimal


def sales_price_variance(
    actual_price: Decimal,
    budgeted_price: Decimal,
    actual_units: Decimal,
) -> Decimal:
    """Sales price variance (DESIGN.md 4.5): ``(AP - BP) * actual_units``."""
    return (to_decimal(actual_price) - to_decimal(budgeted_price)) * to_decimal(actual_units)


def sales_volume_variance(
    actual_units: Decimal,
    budgeted_units: Decimal,
    budgeted_cm_per_unit: Decimal,
) -> Decimal:
    """Sales volume variance (DESIGN.md 4.5): ``(AU - BU) * BCM``.

    This single-product volume variance equals ``mix_i + quantity_i`` from
    :func:`sales_mix_quantity` for the same product.
    """
    return (to_decimal(actual_units) - to_decimal(budgeted_units)) * to_decimal(budgeted_cm_per_unit)


@dataclass(frozen=True)
class ProductSales:
    """Actual/budget units and budgeted CM/unit for one product (DESIGN.md 4.5)."""

    name: str
    actual_units: Decimal
    budgeted_units: Decimal
    budgeted_cm_per_unit: Decimal


@dataclass(frozen=True)
class MixQtyResult:
    """Per-product and total mix/quantity decomposition (DESIGN.md 4.5)."""

    mix: dict[str, Decimal]
    quantity: dict[str, Decimal]
    total_mix: Decimal
    total_quantity: Decimal
    total_volume: Decimal


def sales_mix_quantity(products: Sequence[ProductSales]) -> MixQtyResult:
    """Split the multi-product sales-volume variance into mix and quantity (DESIGN.md 4.5).

    Horngren formulation, per product ``i`` with
    ``budgeted_mix_pct_i = budgeted_units_i / sum(budgeted_units)``:

        ``mix_i      = (actual_units_i - actual_total * budgeted_mix_pct_i) * BCM_i``
        ``quantity_i = (actual_total - budgeted_total) * budgeted_mix_pct_i * BCM_i``

    Invariant (DESIGN.md 4.5): for every product
    ``mix_i + quantity_i == (actual_units_i - budgeted_units_i) * BCM_i`` (its
    single-product sales-volume variance). ``total_volume`` is the sum of those, and
    ``total_mix + total_quantity == total_volume``.

    Raises:
        ValueError: if total budgeted units is zero (budgeted mix is undefined).
    """
    budgeted_total = sum((to_decimal(p.budgeted_units) for p in products), Decimal("0"))
    actual_total = sum((to_decimal(p.actual_units) for p in products), Decimal("0"))
    if budgeted_total == 0:
        raise ValueError("Total budgeted units must be non-zero to compute sales mix.")

    mix: dict[str, Decimal] = {}
    quantity: dict[str, Decimal] = {}
    total_volume = Decimal("0")
    for p in products:
        actual_units = to_decimal(p.actual_units)
        budgeted_units = to_decimal(p.budgeted_units)
        bcm = to_decimal(p.budgeted_cm_per_unit)
        budgeted_mix_pct = budgeted_units / budgeted_total
        mix[p.name] = (actual_units - actual_total * budgeted_mix_pct) * bcm
        quantity[p.name] = (actual_total - budgeted_total) * budgeted_mix_pct * bcm
        total_volume += (actual_units - budgeted_units) * bcm

    total_mix = sum(mix.values(), Decimal("0"))
    total_quantity = sum(quantity.values(), Decimal("0"))
    return MixQtyResult(
        mix=mix,
        quantity=quantity,
        total_mix=total_mix,
        total_quantity=total_quantity,
        total_volume=total_volume,
    )
