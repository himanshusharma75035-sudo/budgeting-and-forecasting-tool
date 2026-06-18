"""Value-Proposition / Priority-Based budgeting (DESIGN.md 2.5).

Product-defined optimizer (an engineering construction layered on a qualitative method):
1. Default greedy: ``ROI_j = value_score / cost``, sort descending (stable), fund while
   cumulative cost <= cap, skipping items that would breach the cap but continuing to
   consider cheaper later ones.
2. Optional ``optimal=True``: 0/1 knapsack maximizing total ``value_score`` subject to
   ``sum(cost) <= cap``, solved by integer DP over costs scaled to minor units.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.domain.money import to_decimal, to_minor


@dataclass(frozen=True)
class Initiative:
    """A funding candidate with a cost and a (subjective, rubric-scored) value score."""

    name: str
    cost: Decimal
    value_score: Decimal


@dataclass(frozen=True)
class FundingDecision:
    """The funded/deferred split plus aggregate cost, value, and remaining slack."""

    funded: list[str]
    deferred: list[str]
    total_cost: Decimal
    total_value: Decimal
    slack: Decimal


def value_proposition_budget(
    initiatives: Sequence[Initiative],
    cap: Decimal,
    *,
    optimal: bool = False,
) -> FundingDecision:
    """Allocate a budget cap across initiatives (DESIGN.md 2.5).

    Default (``optimal=False``): greedy by descending ROI (``value_score / cost``), stable
    on ties, funding while cumulative cost stays within ``cap`` and skipping over items
    that would exceed it.

    With ``optimal=True``: a 0/1 knapsack that maximizes total value subject to the cap.

    ``slack = cap - total_cost``. Funded and deferred are lists of initiative names; both
    preserve the original input order.
    """
    cap_dec = to_decimal(cap)
    if optimal:
        funded_names = _knapsack(initiatives, cap_dec)
    else:
        funded_names = _greedy(initiatives, cap_dec)

    funded_set = set(funded_names)
    funded: list[str] = []
    deferred: list[str] = []
    total_cost = Decimal("0")
    total_value = Decimal("0")
    for item in initiatives:
        if item.name in funded_set:
            funded.append(item.name)
            total_cost += to_decimal(item.cost)
            total_value += to_decimal(item.value_score)
        else:
            deferred.append(item.name)

    return FundingDecision(
        funded=funded,
        deferred=deferred,
        total_cost=total_cost,
        total_value=total_value,
        slack=cap_dec - total_cost,
    )


def _greedy(initiatives: Sequence[Initiative], cap: Decimal) -> list[str]:
    """Greedy fund by descending ROI (stable), skipping items that overflow the cap."""
    indexed = list(enumerate(initiatives))
    indexed.sort(
        key=lambda pair: to_decimal(pair[1].value_score) / to_decimal(pair[1].cost),
        reverse=True,
    )
    chosen: list[str] = []
    spent = Decimal("0")
    for _, item in indexed:
        cost = to_decimal(item.cost)
        if spent + cost <= cap:
            chosen.append(item.name)
            spent += cost
    return chosen


def _knapsack(initiatives: Sequence[Initiative], cap: Decimal) -> list[str]:
    """0/1 knapsack maximizing total value_score under the cap (integer DP on minor units)."""
    capacity = to_minor(cap)
    if capacity < 0:
        return []
    weights = [to_minor(item.cost) for item in initiatives]
    # Scale values to integers (minor units) so the DP comparison is exact.
    values = [to_minor(item.value_score) for item in initiatives]

    n = len(initiatives)
    # dp[w] = best achievable value using capacity w; keep[i][w] for reconstruction.
    dp = [0] * (capacity + 1)
    keep = [[False] * (capacity + 1) for _ in range(n)]
    for i in range(n):
        wi, vi = weights[i], values[i]
        if wi < 0:
            continue
        for w in range(capacity, wi - 1, -1):
            candidate = dp[w - wi] + vi
            if candidate > dp[w]:
                dp[w] = candidate
                keep[i][w] = True

    chosen_idx: list[int] = []
    w = capacity
    for i in range(n - 1, -1, -1):
        if keep[i][w]:
            chosen_idx.append(i)
            w -= weights[i]
    chosen_set = set(chosen_idx)
    return [item.name for i, item in enumerate(initiatives) if i in chosen_set]
