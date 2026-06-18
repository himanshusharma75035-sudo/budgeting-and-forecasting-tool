"""Variance sign / polarity helpers (DESIGN.md 4.2).

Every variance in this domain is computed left-to-right as ``Actual - Comparison``.
The *raw sign* of that difference is not sufficient to decide whether the outcome is
good or bad: for COST/expense accounts a positive variance (spent more) is
**unfavorable**, while for REVENUE/income accounts a positive variance (earned more) is
**favorable**. Favorable/unfavorable is therefore always derived from the
:class:`~app.domain.enums.AccountType`, never from the raw sign alone.
"""

from __future__ import annotations

from decimal import Decimal

from app.domain.enums import AccountType, VarianceStatus, is_cost, sign_factor


def is_favorable(account_type: AccountType, variance: Decimal) -> bool:
    """Return ``True`` when ``variance`` is favorable for ``account_type`` (DESIGN.md 4.2).

    Cost/expense accounts: favorable when ``variance < 0`` (spent less than comparison).
    Revenue/income (and other) accounts: favorable when ``variance > 0`` (earned more).
    A zero variance is *not* favorable (use :func:`status` to detect NEUTRAL).
    """
    if is_cost(account_type):
        return variance < 0
    return variance > 0


def favorable_variance(account_type: AccountType, variance: Decimal) -> Decimal:
    """Re-orient ``variance`` so that *positive == good* for every account type.

    Defined as ``variance * sign_factor(account_type)`` (DESIGN.md 4.2). Because
    :func:`~app.domain.enums.sign_factor` is ``-1`` for cost/expense accounts and ``+1``
    for revenue/income, the result is the favorable-positive form usable on dashboards
    where larger is always better.
    """
    return variance * sign_factor(account_type)


def status(
    account_type: AccountType,
    variance: Decimal,
    *,
    neutral_eps: Decimal = Decimal("0"),
) -> VarianceStatus:
    """Classify ``variance`` as FAVORABLE / UNFAVORABLE / NEUTRAL (DESIGN.md 4.2).

    ``NEUTRAL`` when ``abs(variance) <= neutral_eps`` (default ``0`` => only an exact
    zero is neutral). Otherwise FAVORABLE/UNFAVORABLE via :func:`is_favorable`.
    """
    if abs(variance) <= neutral_eps:
        return VarianceStatus.NEUTRAL
    return VarianceStatus.FAVORABLE if is_favorable(account_type, variance) else VarianceStatus.UNFAVORABLE
