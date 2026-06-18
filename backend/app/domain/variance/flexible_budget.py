"""Flexible budget and the static/flexible/volume variance hierarchy (DESIGN.md 4.1).

A *flexible budget* re-states the budget at the **actual** activity level so that the
static (master-budget) variance can be split into the part caused by activity volume
(the sales-volume variance) and the part caused by everything else at that volume (the
flexible-budget variance). The classic Horngren three-way decomposition:

    static_variance        = Actual - Static budget
    flexible_budget_variance = Actual - Flexible budget
    sales_volume_variance    = Flexible budget - Static budget

Invariant (DESIGN.md 4.1):
    ``static_variance == flexible_budget_variance + sales_volume_variance``
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.money import to_decimal


def flexible_budget(
    budgeted_rate_per_unit: Decimal,
    actual_units: Decimal,
    budgeted_fixed: Decimal,
) -> Decimal:
    """Flex the budget to the actual activity level (DESIGN.md 4.1).

    Formula: ``flexible = budgeted_rate_per_unit * actual_units + budgeted_fixed``.
    """
    rate = to_decimal(budgeted_rate_per_unit)
    units = to_decimal(actual_units)
    fixed = to_decimal(budgeted_fixed)
    return rate * units + fixed


@dataclass(frozen=True)
class VarianceHierarchy:
    """The three levels of the static-budget decomposition (DESIGN.md 4.1)."""

    static_variance: Decimal
    flexible_budget_variance: Decimal
    sales_volume_variance: Decimal


def variance_hierarchy(
    actual: Decimal,
    flexible: Decimal,
    static: Decimal,
) -> VarianceHierarchy:
    """Decompose the static-budget variance into flex + volume parts (DESIGN.md 4.1).

    Formulas:
        ``flexible_budget_variance = actual - flexible``
        ``sales_volume_variance    = flexible - static``
        ``static_variance          = actual - static``

    By construction the invariant
    ``static_variance == flexible_budget_variance + sales_volume_variance`` holds
    exactly under :class:`decimal.Decimal` arithmetic.
    """
    actual = to_decimal(actual)
    flexible = to_decimal(flexible)
    static = to_decimal(static)
    return VarianceHierarchy(
        static_variance=actual - static,
        flexible_budget_variance=actual - flexible,
        sales_volume_variance=flexible - static,
    )
