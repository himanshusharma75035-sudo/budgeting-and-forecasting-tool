"""Orthogonal budgeting modifiers (DESIGN.md 2.7).

- Flexible mode: re-evaluate variable lines at actual volume; fixed lines unchanged.
- Rolling mode: a scheduler that, at period close, exposes the next ``N`` monthly horizon.
"""

from __future__ import annotations

from decimal import Decimal

from app.domain.money import to_decimal
from app.domain.periods import add_months


def flexible_budget_allowance(
    std_variable_cost_per_unit: Decimal,
    actual_volume: Decimal,
    budgeted_fixed_cost: Decimal,
) -> Decimal:
    """Flexible budget allowance (DESIGN.md 2.7).

    Formula: ``FlexAllowance = (StdVariableCostPerUnit * ActualVolume) + BudgetedFixedCost``.
    Variable lines flex with actual volume; fixed lines are unchanged.
    """
    return (
        to_decimal(std_variable_cost_per_unit) * to_decimal(actual_volume)
        + to_decimal(budgeted_fixed_cost)
    )


def rolling_horizon(as_of_period_key: int, horizon: int) -> list[int]:
    """Next ``horizon`` monthly period keys strictly AFTER ``as_of_period_key`` (DESIGN.md 2.7).

    At period close the horizon is ``[t+1 .. t+N]``: drop the oldest, append the new, keep
    ``N`` constant.

    >>> rolling_horizon(202412, 3)
    [202501, 202502, 202503]
    """
    return [add_months(as_of_period_key, offset) for offset in range(1, horizon + 1)]
