"""Variance insights & narrative (roadmap 0.7).

Turns per-account budget-vs-actual results into ranked drivers plus a plain-language commentary —
"what moved, and which lines drove it." Deterministic and dependency-free, so it always works
offline; an optional LLM can *enrich* the prose later (see ``app.services.ai``), but the structured
insight and a readable narrative are produced here with no external calls.

Polarity is carried by ``favorable_variance`` (signed: **+ favourable** to profit, **- unfavourable**),
already derived from the account type upstream — so summing it across accounts gives the net P&L
impact, and ranking by it surfaces the biggest helps and drags.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.domain.enums import VarianceStatus

_ZERO = Decimal("0")


@dataclass(frozen=True)
class VarianceItem:
    """One account's aggregated variance over the reporting scope (input to the engine)."""

    code: str
    label: str
    category: str | None
    favorable_variance: Decimal  # signed: + favourable, - unfavourable
    actual: Decimal
    comparison: Decimal
    is_material: bool


@dataclass(frozen=True)
class InsightDriver:
    code: str
    label: str
    category: str | None
    favorable_variance: Decimal
    actual: Decimal
    comparison: Decimal
    is_material: bool


@dataclass(frozen=True)
class VarianceInsight:
    net_favorable: Decimal
    status: VarianceStatus
    favorable_total: Decimal
    unfavorable_total: Decimal
    top_favorable: list[InsightDriver]
    top_unfavorable: list[InsightDriver]
    by_category: list[InsightDriver]
    material: list[InsightDriver]


def build_insights(items: Sequence[VarianceItem], *, top_n: int = 3) -> VarianceInsight:
    """Rank drivers and summarise the net favourable/unfavourable picture."""
    drivers = [
        InsightDriver(
            code=i.code,
            label=i.label,
            category=i.category,
            favorable_variance=i.favorable_variance,
            actual=i.actual,
            comparison=i.comparison,
            is_material=i.is_material,
        )
        for i in items
    ]
    net = sum((d.favorable_variance for d in drivers), _ZERO)
    fav_total = sum((d.favorable_variance for d in drivers if d.favorable_variance > 0), _ZERO)
    unfav_total = sum((d.favorable_variance for d in drivers if d.favorable_variance < 0), _ZERO)
    st = (
        VarianceStatus.FAVORABLE
        if net > 0
        else VarianceStatus.UNFAVORABLE
        if net < 0
        else VarianceStatus.NEUTRAL
    )

    by_fav_desc = sorted(drivers, key=lambda d: d.favorable_variance, reverse=True)
    top_favorable = [d for d in by_fav_desc if d.favorable_variance > 0][:top_n]
    top_unfavorable = [d for d in reversed(by_fav_desc) if d.favorable_variance < 0][:top_n]
    material = sorted(
        (d for d in drivers if d.is_material), key=lambda d: abs(d.favorable_variance), reverse=True
    )
    return VarianceInsight(
        net_favorable=net,
        status=st,
        favorable_total=fav_total,
        unfavorable_total=unfav_total,
        top_favorable=top_favorable,
        top_unfavorable=top_unfavorable,
        by_category=_aggregate_by_category(drivers),
        material=material,
    )


def _aggregate_by_category(drivers: Sequence[InsightDriver]) -> list[InsightDriver]:
    sums: dict[str, list[Decimal]] = defaultdict(lambda: [_ZERO, _ZERO, _ZERO])
    flagged: dict[str, bool] = defaultdict(bool)
    for d in drivers:
        cat = d.category or "Other"
        bucket = sums[cat]
        bucket[0] += d.favorable_variance
        bucket[1] += d.actual
        bucket[2] += d.comparison
        flagged[cat] = flagged[cat] or d.is_material
    out = [
        InsightDriver(
            code=cat,
            label=cat,
            category=cat,
            favorable_variance=v[0],
            actual=v[1],
            comparison=v[2],
            is_material=flagged[cat],
        )
        for cat, v in sums.items()
    ]
    return sorted(out, key=lambda d: d.favorable_variance, reverse=True)


def compose_narrative(insight: VarianceInsight, fmt: Callable[[Decimal], str]) -> str:
    """Compose a markdown commentary. ``fmt`` renders a Decimal amount (e.g. INR compact)."""
    parts: list[str] = []
    if insight.status == VarianceStatus.NEUTRAL:
        parts.append("**Performance is on plan** for the selected period — no net variance.")
    else:
        word = "favourable" if insight.status == VarianceStatus.FAVORABLE else "unfavourable"
        parts.append(f"**Net variance is {word} at {fmt(abs(insight.net_favorable))}** for the selected period.")

    if insight.top_unfavorable:
        items = ", ".join(f"{d.label} ({fmt(abs(d.favorable_variance))})" for d in insight.top_unfavorable)
        parts.append(f"Biggest drags: {items}.")
    if insight.top_favorable:
        items = ", ".join(f"{d.label} ({fmt(d.favorable_variance)})" for d in insight.top_favorable)
        parts.append(f"Largest offsets: {items}.")
    if insight.material:
        names = ", ".join(d.label for d in insight.material[:5])
        n = len(insight.material)
        parts.append(f"{n} line item{'s' if n != 1 else ''} breached the materiality threshold: {names}.")
    return " ".join(parts)
