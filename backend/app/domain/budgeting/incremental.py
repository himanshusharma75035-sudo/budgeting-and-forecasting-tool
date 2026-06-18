"""Incremental budgeting (DESIGN.md 2.3).

Product-defined formula (a deliberate engineering formalization, not source canon):
``Budget_i = PriorActual_i * (1 + g_i) + Adjustment_i``, using prior **actuals** as the
baseline. All money math is exact via :class:`decimal.Decimal`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from app.domain.money import to_decimal


@dataclass(frozen=True)
class IncrementalLine:
    """A single prior-actual line plus its growth factor and one-off adjustment."""

    account_code: str
    prior_actual: Decimal
    growth_pct: Decimal = field(default_factory=lambda: Decimal("0"))
    one_off: Decimal = field(default_factory=lambda: Decimal("0"))


@dataclass(frozen=True)
class BudgetLine:
    """A produced budget line. Either ``account_code`` or ``name`` identifies it."""

    account_code: str | None
    name: str | None
    amount: Decimal


def incremental_budget(lines: Sequence[IncrementalLine]) -> list[BudgetLine]:
    """Build budget lines via the incremental method (DESIGN.md 2.3).

    Formula: ``amount = prior_actual * (1 + growth_pct) + one_off``.

    All inputs are coerced through :func:`app.domain.money.to_decimal` so callers may
    pass ``int``/``float``/``str`` safely. Returns one :class:`BudgetLine` per input,
    with ``account_code`` carried through and ``name`` left ``None``.
    """
    one = Decimal("1")
    result: list[BudgetLine] = []
    for line in lines:
        prior_actual = to_decimal(line.prior_actual)
        growth_pct = to_decimal(line.growth_pct)
        one_off = to_decimal(line.one_off)
        amount = prior_actual * (one + growth_pct) + one_off
        result.append(BudgetLine(account_code=line.account_code, name=None, amount=amount))
    return result
