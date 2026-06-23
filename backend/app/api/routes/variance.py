"""Variance analysis endpoints (DESIGN.md 4).

These are thin: the aggregation and assembly live in :mod:`app.services.variance_query` so the
on-screen analysis and the downloadable board pack share one source of truth. Endpoints map the
domain results to DTOs and (for insights) add the optional AI narrative polish.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.domain.variance import InsightDriver, compose_narrative
from app.schemas import (
    BridgeOut,
    BridgeStepOut,
    InsightDriverOut,
    VarianceComputeRequest,
    VarianceInsightOut,
    VarianceRowOut,
)
from app.services.ai import enrich_narrative
from app.services.variance_query import (
    compute_bridge,
    compute_insight,
    compute_rows,
    inr_compact,
)

router = APIRouter(tags=["variance"])


@router.post("/variance/compute", response_model=list[VarianceRowOut])
def compute(req: VarianceComputeRequest, session: Session = Depends(get_session)) -> list[VarianceRowOut]:
    return [
        VarianceRowOut(
            account_code=r.account_code,
            period=r.period,
            account_type=r.account_type,
            actual=r.actual,
            comparison=r.comparison,
            variance=r.variance,
            favorable_variance=r.favorable_variance,
            variance_pct=r.variance_pct,
            status=r.status.value,
            is_material=r.is_material,
        )
        for r in compute_rows(session, req)
    ]


@router.post("/variance/bridge", response_model=BridgeOut)
def bridge(req: VarianceComputeRequest, session: Session = Depends(get_session)) -> BridgeOut:
    """Net-income bridge grouped by Schedule III category: start (comparison) + favorable
    contribution per category = end (actual). Grouping keeps the waterfall readable (~10 bars
    instead of one per account)."""
    result = compute_bridge(session, req)
    return BridgeOut(
        start=result.start,
        steps=[BridgeStepOut(label=s.label, delta=s.delta) for s in result.steps],
        end=result.end,
    )


def _driver_out(d: InsightDriver) -> InsightDriverOut:
    return InsightDriverOut(
        code=d.code,
        label=d.label,
        category=d.category,
        favorable_variance=d.favorable_variance,
        actual=d.actual,
        comparison=d.comparison,
        is_material=d.is_material,
    )


@router.post("/variance/insights", response_model=VarianceInsightOut)
def insights(req: VarianceComputeRequest, session: Session = Depends(get_session)) -> VarianceInsightOut:
    """Ranked variance drivers + an auto-generated narrative.

    Deterministic by default (works fully offline); if AI is enabled in settings the prose is
    polished by Claude, otherwise the deterministic narrative is returned unchanged.
    """
    insight = compute_insight(session, req)
    narrative = compose_narrative(insight, inr_compact)
    polished = enrich_narrative(
        narrative, instruction=f"Context: {req.base_scenario.value} vs {req.compare_scenario.value}."
    )
    return VarianceInsightOut(
        net_favorable=insight.net_favorable,
        status=insight.status.value,
        favorable_total=insight.favorable_total,
        unfavorable_total=insight.unfavorable_total,
        top_favorable=[_driver_out(d) for d in insight.top_favorable],
        top_unfavorable=[_driver_out(d) for d in insight.top_unfavorable],
        by_category=[_driver_out(d) for d in insight.by_category],
        material=[_driver_out(d) for d in insight.material],
        narrative=polished or narrative,
        ai_generated=polished is not None,
    )
