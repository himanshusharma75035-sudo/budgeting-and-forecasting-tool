"""Activity-Based Budgeting / ABB (DESIGN.md 2.4).

Source-grounded formulas (CFI / Wall Street Mojo):
``R_a = CostPool_a / DriverUnits_a`` ; ``Budget_a = V_a * R_a`` ;
``Total = sum(V_a * R_a) + FixedCosts``.

The driver rate keeps full :class:`decimal.Decimal` precision (no pre-rounding); only the
persistence boundary rounds. DESIGN.md's worked total of 746,104 used display-rounded
rates, whereas we carry full precision.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.domain.budgeting.incremental import BudgetLine
from app.domain.money import to_decimal


@dataclass(frozen=True)
class Activity:
    """An activity with its prior cost pool, prior driver units, and forecast volume."""

    name: str
    prior_cost_pool: Decimal
    prior_driver_units: Decimal
    forecast_driver_volume: Decimal


@dataclass(frozen=True)
class ABBResult:
    """Per-activity budget lines plus fixed costs and the grand total."""

    lines: list[BudgetLine]
    fixed_costs: Decimal
    total: Decimal


def activity_based_budget(
    activities: Sequence[Activity],
    fixed_costs: Decimal = Decimal("0"),
) -> ABBResult:
    """Build an activity-based budget (DESIGN.md 2.4).

    For each activity: ``rate = prior_cost_pool / prior_driver_units`` (full Decimal
    precision, not pre-rounded) and ``amount = rate * forecast_driver_volume``. The total
    is ``sum(line.amount) + fixed_costs``.

    Raises:
        ValueError: if any activity has ``prior_driver_units == 0`` (undefined rate).
    """
    fixed = to_decimal(fixed_costs)
    lines: list[BudgetLine] = []
    activities_total = Decimal("0")
    for activity in activities:
        prior_driver_units = to_decimal(activity.prior_driver_units)
        if prior_driver_units == 0:
            raise ValueError(
                f"activity {activity.name!r} has zero prior driver units; rate is undefined"
            )
        rate = to_decimal(activity.prior_cost_pool) / prior_driver_units
        amount = rate * to_decimal(activity.forecast_driver_volume)
        lines.append(BudgetLine(account_code=None, name=activity.name, amount=amount))
        activities_total += amount
    return ABBResult(lines=lines, fixed_costs=fixed, total=activities_total + fixed)
