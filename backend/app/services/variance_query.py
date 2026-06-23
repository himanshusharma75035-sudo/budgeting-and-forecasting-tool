"""Shared variance query + assembly (DESIGN.md 4).

Single source of truth for scenario aggregation, period scoping, and the three derived
artefacts — the per-(account, period) detail rows, the per-account ranked insight, and the
category contribution bridge. Both the ``/variance/*`` API endpoints and the downloadable
board pack consume these, so the on-screen analysis and the exported workbook can never drift.

All money math is exact ``Decimal``; favourable/unfavourable polarity is always derived from
the account type, never from the raw sign alone.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from sqlmodel import Session, select

from app.db.models import Account, Entry
from app.domain.enums import AccountType, Scenario, VarianceStatus
from app.domain.money import from_minor
from app.domain.periods import format_period, parse_period
from app.domain.variance import (
    Bridge,
    BridgeStep,
    MaterialityThreshold,
    VarianceInsight,
    VarianceItem,
    budget_vs_actual,
    build_bridge,
    build_insights,
    favorable_variance,
    is_material,
)
from app.schemas import VarianceComputeRequest

Key = tuple[int, int]  # (account_id, period_key)

_ZERO = Decimal("0")


def inr_compact(value: Decimal) -> str:
    """Indian-format a Decimal amount for narrative prose, e.g. ₹1.20 Cr / ₹9.50 L / ₹4,200.

    Shared by the insights endpoint and the board-pack export so both narratives read identically.
    """
    n = abs(value)
    sign = "-" if value < 0 else ""
    if n >= Decimal("1e7"):
        return f"{sign}₹{n / Decimal('1e7'):.2f} Cr"
    if n >= Decimal("1e5"):
        return f"{sign}₹{n / Decimal('1e5'):.2f} L"
    return f"{sign}₹{n:,.0f}"


@dataclass(frozen=True)
class VarianceRowData:
    """One (account, period) budget-vs-actual line — the richest shape; callers project from it."""

    account_code: str
    account_name: str
    account_type: AccountType
    category: str | None
    period: str
    actual: Decimal
    comparison: Decimal
    variance: Decimal
    favorable_variance: Decimal
    variance_pct: float | None
    status: VarianceStatus
    is_material: bool


# --- primitives ------------------------------------------------------------


def period_bounds(req: VarianceComputeRequest) -> tuple[int | None, int | None]:
    lo = parse_period(req.period_from) if req.period_from else None
    hi = parse_period(req.period_to) if req.period_to else None
    return lo, hi


def aggregate_scenario(
    session: Session,
    scenario: Scenario,
    *,
    budget_version_id: int | None,
    forecast_run_id: int | None,
    lo: int | None,
    hi: int | None,
) -> dict[Key, Decimal]:
    """Sum entry amounts to (account, period) totals for one scenario within the bounds."""
    stmt = select(Entry).where(Entry.scenario == scenario)
    if scenario == Scenario.BUDGET and budget_version_id is not None:
        stmt = stmt.where(Entry.budget_version_id == budget_version_id)
    if scenario == Scenario.FORECAST and forecast_run_id is not None:
        stmt = stmt.where(Entry.forecast_run_id == forecast_run_id)
    if lo is not None:
        stmt = stmt.where(Entry.period_key >= lo)
    if hi is not None:
        stmt = stmt.where(Entry.period_key <= hi)
    agg: dict[Key, Decimal] = defaultdict(lambda: _ZERO)
    for e in session.exec(stmt).all():
        agg[(e.account_id, e.period_key)] += from_minor(e.amount_minor, e.minor_unit_scale)
    return agg


def load_accounts(session: Session) -> dict[int, Account]:
    return {a.account_id: a for a in session.exec(select(Account)).all() if a.account_id is not None}


def _base_and_compare(
    session: Session, req: VarianceComputeRequest
) -> tuple[dict[Key, Decimal], dict[Key, Decimal], dict[int, Account]]:
    lo, hi = period_bounds(req)
    base = aggregate_scenario(
        session, req.base_scenario,
        budget_version_id=req.budget_version_id, forecast_run_id=req.forecast_run_id, lo=lo, hi=hi,
    )
    compare = aggregate_scenario(
        session, req.compare_scenario,
        budget_version_id=req.budget_version_id, forecast_run_id=req.forecast_run_id, lo=lo, hi=hi,
    )
    return base, compare, load_accounts(session)


# --- assembly --------------------------------------------------------------


def compute_rows(session: Session, req: VarianceComputeRequest) -> list[VarianceRowData]:
    """Per-(account, period) budget-vs-actual rows, scoped to the comparison scenario's periods."""
    base, compare, accts = _base_and_compare(session, req)
    threshold = MaterialityThreshold(pct_threshold=req.pct_threshold, abs_threshold=req.abs_threshold)

    # Scope to the comparison scenario's periods (a budget/forecast variance report is defined over
    # the periods that scenario covers); avoids "vs zero" noise for unbudgeted months.
    scope = set(compare) if compare else set(base)
    rows: list[VarianceRowData] = []
    for key in sorted(scope):
        account_id, period_key = key
        acct = accts.get(account_id)
        if acct is None:
            continue
        actual = base.get(key, _ZERO)
        comparison = compare.get(key, _ZERO)
        v = budget_vs_actual(actual, comparison, acct.account_type)
        rows.append(
            VarianceRowData(
                account_code=acct.account_code,
                account_name=acct.account_name,
                account_type=acct.account_type,
                category=acct.account_category,
                period=format_period(period_key),
                actual=actual,
                comparison=comparison,
                variance=v.variance,
                favorable_variance=favorable_variance(acct.account_type, v.variance),
                variance_pct=v.variance_pct,
                status=v.status,
                is_material=is_material(v.variance, comparison, threshold),
            )
        )
    return rows


def _per_account_totals(
    base: dict[Key, Decimal], compare: dict[Key, Decimal]
) -> tuple[dict[int, Decimal], dict[int, Decimal]]:
    """Roll (account, period) totals up to per-account totals over the comparison scope."""
    keys = set(compare) or set(base)
    actual_by: dict[int, Decimal] = defaultdict(lambda: _ZERO)
    comp_by: dict[int, Decimal] = defaultdict(lambda: _ZERO)
    for key in keys:
        aid = key[0]
        actual_by[aid] += base.get(key, _ZERO)
        comp_by[aid] += compare.get(key, _ZERO)
    return actual_by, comp_by


def compute_insight(session: Session, req: VarianceComputeRequest) -> VarianceInsight:
    """Per-account ranked drivers + net favourable/unfavourable picture (period totals)."""
    base, compare, accts = _base_and_compare(session, req)
    threshold = MaterialityThreshold(pct_threshold=req.pct_threshold, abs_threshold=req.abs_threshold)
    actual_by, comp_by = _per_account_totals(base, compare)

    items: list[VarianceItem] = []
    for aid in set(actual_by) | set(comp_by):
        acct = accts.get(aid)
        if acct is None:
            continue
        actual = actual_by.get(aid, _ZERO)
        comparison = comp_by.get(aid, _ZERO)
        var = actual - comparison
        items.append(
            VarianceItem(
                code=acct.account_code,
                label=acct.account_name or acct.account_code,
                category=acct.account_category,
                favorable_variance=favorable_variance(acct.account_type, var),
                actual=actual,
                comparison=comparison,
                is_material=is_material(var, comparison, threshold),
            )
        )
    return build_insights(items)


def compute_bridge(session: Session, req: VarianceComputeRequest) -> Bridge:
    """Net contribution bridge grouped by Schedule III category: start (comparison) + favourable
    contribution per category = end (actual)."""
    base, compare, accts = _base_and_compare(session, req)
    actual_by, comp_by = _per_account_totals(base, compare)

    start = _ZERO
    by_category: dict[str, Decimal] = defaultdict(lambda: _ZERO)
    for account_id in set(comp_by) | set(actual_by):
        acct = accts.get(account_id)
        if acct is None:
            continue
        comp_total = comp_by.get(account_id, _ZERO)
        actual_total = actual_by.get(account_id, _ZERO)
        start += comp_total * acct.sign_factor
        delta = favorable_variance(acct.account_type, actual_total - comp_total)
        category = acct.account_category or acct.account_type.value
        by_category[category] += delta

    # drop ~zero categories; sort favourable (positive) first, then unfavourable
    steps = [
        BridgeStep(label=cat, delta=d)
        for cat, d in sorted(by_category.items(), key=lambda kv: kv[1], reverse=True)
        if abs(d) > Decimal("0.005")
    ]
    return build_bridge(start, steps)
