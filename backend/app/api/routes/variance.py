"""Variance analysis endpoints (DESIGN.md 4)."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db.models import Account, Entry
from app.db.session import get_session
from app.domain.enums import Scenario
from app.domain.money import from_minor
from app.domain.periods import format_period, parse_period
from app.domain.variance import (
    BridgeStep,
    MaterialityThreshold,
    budget_vs_actual,
    build_bridge,
    favorable_variance,
    is_material,
)
from app.schemas import BridgeOut, BridgeStepOut, VarianceComputeRequest, VarianceRowOut

router = APIRouter(tags=["variance"])

Key = tuple[int, int]  # (account_id, period_key)


def _aggregate(
    session: Session,
    scenario: Scenario,
    *,
    budget_version_id: int | None,
    forecast_run_id: int | None,
    lo: int | None,
    hi: int | None,
) -> dict[Key, Decimal]:
    stmt = select(Entry).where(Entry.scenario == scenario)
    if scenario == Scenario.BUDGET and budget_version_id is not None:
        stmt = stmt.where(Entry.budget_version_id == budget_version_id)
    if scenario == Scenario.FORECAST and forecast_run_id is not None:
        stmt = stmt.where(Entry.forecast_run_id == forecast_run_id)
    if lo is not None:
        stmt = stmt.where(Entry.period_key >= lo)
    if hi is not None:
        stmt = stmt.where(Entry.period_key <= hi)
    agg: dict[Key, Decimal] = defaultdict(lambda: Decimal("0"))
    for e in session.exec(stmt).all():
        agg[(e.account_id, e.period_key)] += from_minor(e.amount_minor, e.minor_unit_scale)
    return agg


def _bounds(req: VarianceComputeRequest) -> tuple[int | None, int | None]:
    lo = parse_period(req.period_from) if req.period_from else None
    hi = parse_period(req.period_to) if req.period_to else None
    return lo, hi


@router.post("/variance/compute", response_model=list[VarianceRowOut])
def compute(req: VarianceComputeRequest, session: Session = Depends(get_session)) -> list[VarianceRowOut]:
    lo, hi = _bounds(req)
    base = _aggregate(session, req.base_scenario, budget_version_id=req.budget_version_id,
                      forecast_run_id=req.forecast_run_id, lo=lo, hi=hi)
    compare = _aggregate(session, req.compare_scenario, budget_version_id=req.budget_version_id,
                         forecast_run_id=req.forecast_run_id, lo=lo, hi=hi)
    accts = {a.account_id: a for a in session.exec(select(Account)).all()}
    threshold = MaterialityThreshold(pct_threshold=req.pct_threshold, abs_threshold=req.abs_threshold)

    # Scope to the comparison scenario's periods (a budget/forecast variance report is
    # defined over the periods that scenario covers); avoids "vs zero" noise for unbudgeted months.
    scope = set(compare) if compare else set(base)
    rows: list[VarianceRowOut] = []
    for key in sorted(scope):
        account_id, period_key = key
        acct = accts.get(account_id)
        if acct is None:
            continue
        actual = base.get(key, Decimal("0"))
        comparison = compare.get(key, Decimal("0"))
        v = budget_vs_actual(actual, comparison, acct.account_type)
        rows.append(
            VarianceRowOut(
                account_code=acct.account_code,
                period=format_period(period_key),
                account_type=acct.account_type,
                actual=actual,
                comparison=comparison,
                variance=v.variance,
                favorable_variance=favorable_variance(acct.account_type, v.variance),
                variance_pct=v.variance_pct,
                status=v.status.value,
                is_material=is_material(v.variance, comparison, threshold),
            )
        )
    return rows


@router.post("/variance/bridge", response_model=BridgeOut)
def bridge(req: VarianceComputeRequest, session: Session = Depends(get_session)) -> BridgeOut:
    """Net-income bridge grouped by Schedule III category: start (comparison) + favorable
    contribution per category = end (actual). Grouping keeps the waterfall readable (~10 bars
    instead of one per account)."""
    lo, hi = _bounds(req)
    base = _aggregate(session, req.base_scenario, budget_version_id=req.budget_version_id,
                      forecast_run_id=req.forecast_run_id, lo=lo, hi=hi)
    compare = _aggregate(session, req.compare_scenario, budget_version_id=req.budget_version_id,
                         forecast_run_id=req.forecast_run_id, lo=lo, hi=hi)
    accts = {a.account_id: a for a in session.exec(select(Account)).all()}

    # Scope to the comparison scenario's (account, period) keys so actuals are summed over the
    # SAME periods as the budget (mirrors /variance/compute) — otherwise a 3-year actual would be
    # compared against a 1-year budget.
    keys = set(compare) or set(base)
    comp_by_acct: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    actual_by_acct: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    for key in keys:
        aid = key[0]
        comp_by_acct[aid] += compare.get(key, Decimal("0"))
        actual_by_acct[aid] += base.get(key, Decimal("0"))

    start = Decimal("0")
    by_category: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for account_id in set(comp_by_acct) | set(actual_by_acct):
        acct = accts.get(account_id)
        if acct is None:
            continue
        comp_total = comp_by_acct.get(account_id, Decimal("0"))
        actual_total = actual_by_acct.get(account_id, Decimal("0"))
        start += comp_total * acct.sign_factor
        delta = favorable_variance(acct.account_type, actual_total - comp_total)
        category = acct.account_category or acct.account_type.value
        by_category[category] += delta

    # drop ~zero categories; sort favorable (positive) first, then unfavorable
    steps = [
        BridgeStep(label=cat, delta=d)
        for cat, d in sorted(by_category.items(), key=lambda kv: kv[1], reverse=True)
        if abs(d) > Decimal("0.005")
    ]
    result = build_bridge(start, steps)
    return BridgeOut(
        start=result.start,
        steps=[BridgeStepOut(label=s.label, delta=s.delta) for s in result.steps],
        end=result.end,
    )
