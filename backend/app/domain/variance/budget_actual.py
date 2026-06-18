"""Budget-vs-actual variance (DESIGN.md 4.3).

The headline variance for any P&L line: ``variance = Actual - Comparison`` where the
comparison is the budget (or forecast). The percentage is expressed against the
**absolute value of the comparison** so the sign of the percentage tracks the sign of
the variance regardless of whether the budget was positive or negative.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.enums import AccountType, VarianceStatus
from app.domain.money import to_decimal
from app.domain.variance.sign import favorable_variance, is_favorable, status


@dataclass(frozen=True)
class BudgetActualVariance:
    """Result of a single budget-vs-actual comparison (DESIGN.md 4.3)."""

    actual: Decimal
    comparison: Decimal
    variance: Decimal
    favorable_variance: Decimal
    variance_pct: float | None
    status: VarianceStatus
    favorable: bool


def budget_vs_actual(
    actual: Decimal,
    comparison: Decimal,
    account_type: AccountType,
) -> BudgetActualVariance:
    """Compute the budget-vs-actual variance for one line (DESIGN.md 4.3).

    Formula:
        ``variance = actual - comparison``
        ``variance_pct = variance / |comparison| * 100``  (``None`` when comparison == 0)

    Using ``|comparison|`` (DESIGN.md 4.3) keeps the percentage sign aligned with the
    raw variance sign. Favorable/unfavorable polarity is derived from ``account_type``,
    never from the raw sign alone.
    """
    actual = to_decimal(actual)
    comparison = to_decimal(comparison)
    variance = actual - comparison
    variance_pct: float | None
    if comparison != 0:
        variance_pct = float(variance / abs(comparison) * 100)
    else:
        variance_pct = None
    return BudgetActualVariance(
        actual=actual,
        comparison=comparison,
        variance=variance,
        favorable_variance=favorable_variance(account_type, variance),
        variance_pct=variance_pct,
        status=status(account_type, variance),
        favorable=is_favorable(account_type, variance),
    )
