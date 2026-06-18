"""Zero-Based Budgeting / ZBB (DESIGN.md 2.6).

Source-derived rank-and-fund algorithm (Wikipedia / AccountingTools / eFinanceManager):
rank ALL decision packages org-wide by ``Benefit/Cost`` (``rank_by="ratio"``) or net
``Benefit - Cost`` (``rank_by="net"``) descending, then fund top-down while cumulative
cost stays within the funding envelope.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.domain.money import to_decimal


@dataclass(frozen=True)
class DecisionPackage:
    """An independently-justifiable package with a cost and an expected benefit."""

    name: str
    cost: Decimal
    benefit: Decimal


@dataclass(frozen=True)
class ZBBResult:
    """The funded/unfunded split, totals, and the full ranked order of package names."""

    funded: list[str]
    unfunded: list[str]
    total_cost: Decimal
    remaining_funds: Decimal
    ranking: list[str]


def zero_based_budget(
    packages: Sequence[DecisionPackage],
    total_funds: Decimal,
    *,
    rank_by: str = "ratio",
) -> ZBBResult:
    """Rank and fund decision packages from zero (DESIGN.md 2.6).

    ``rank_by`` is ``"ratio"`` (``benefit / cost``) or ``"net"`` (``benefit - cost``);
    packages are ranked descending by the chosen criterion (stable on ties). Funding is
    top-down while cumulative cost <= ``total_funds``; a package that does not fit is
    skipped and ranking continues. ``remaining_funds = total_funds - total_cost``.

    Raises:
        ValueError: if ``rank_by`` is not ``"ratio"`` or ``"net"``.
    """
    if rank_by not in {"ratio", "net"}:
        raise ValueError(f"rank_by must be 'ratio' or 'net', got {rank_by!r}")

    funds = to_decimal(total_funds)

    def score(pkg: DecisionPackage) -> Decimal:
        benefit = to_decimal(pkg.benefit)
        cost = to_decimal(pkg.cost)
        if rank_by == "ratio":
            return benefit / cost
        return benefit - cost

    indexed = list(enumerate(packages))
    indexed.sort(key=lambda pair: score(pair[1]), reverse=True)
    ranking = [pkg.name for _, pkg in indexed]

    funded: list[str] = []
    funded_set: set[str] = set()
    spent = Decimal("0")
    for _, pkg in indexed:
        cost = to_decimal(pkg.cost)
        if spent + cost <= funds:
            funded.append(pkg.name)
            funded_set.add(pkg.name)
            spent += cost

    unfunded = [pkg.name for pkg in packages if pkg.name not in funded_set]

    return ZBBResult(
        funded=funded,
        unfunded=unfunded,
        total_cost=spent,
        remaining_funds=funds - spent,
        ranking=ranking,
    )
