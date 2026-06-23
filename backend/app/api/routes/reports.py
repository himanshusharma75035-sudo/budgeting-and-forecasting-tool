"""Report exports (roadmap 0.8).

Turns a variance request into a downloadable, board-ready Excel pack. Reuses the shared variance
query/assembly so the workbook matches the on-screen analysis exactly.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlmodel import Session

from app.db.session import get_session
from app.domain.reporting import BoardRow, ReportMeta, build_board_pack
from app.domain.variance import compose_narrative
from app.schemas import VarianceComputeRequest
from app.services.variance_query import (
    compute_bridge,
    compute_insight,
    compute_rows,
    inr_compact,
)

router = APIRouter(tags=["reports"])

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _period_label(req: VarianceComputeRequest) -> str:
    lo, hi = req.period_from, req.period_to
    if lo and hi:
        return lo if lo == hi else f"{lo} – {hi}"
    if lo:
        return f"from {lo}"
    if hi:
        return f"through {hi}"
    return "All periods"


@router.post("/reports/variance-pack.xlsx")
def variance_pack(req: VarianceComputeRequest, session: Session = Depends(get_session)) -> Response:
    """Download the variance analysis as a formatted multi-tab Excel board pack."""
    rows = compute_rows(session, req)
    insight = compute_insight(session, req)
    bridge = compute_bridge(session, req)
    narrative = compose_narrative(insight, inr_compact)

    base = req.base_scenario.value
    compare = req.compare_scenario.value
    meta = ReportMeta(
        title="Variance Analysis — Board Pack",
        subtitle="Budget vs actual with ranked drivers and a contribution bridge",
        base_label=base,
        compare_label=compare,
        period_label=_period_label(req),
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
    )
    board_rows = [
        BoardRow(
            account_code=r.account_code,
            account_name=r.account_name,
            category=r.category or "",
            period=r.period,
            comparison=r.comparison,
            actual=r.actual,
            variance=r.variance,
            variance_pct=r.variance_pct,
            status=r.status.value,
            is_material=r.is_material,
        )
        for r in rows
    ]

    content = build_board_pack(meta, board_rows, insight, narrative, bridge)
    filename = f"variance-board-pack-{base}-vs-{compare}.xlsx".lower()
    return Response(
        content=content,
        media_type=_XLSX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
