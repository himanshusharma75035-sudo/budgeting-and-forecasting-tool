"""Period reference endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, col, select

from app.db.models import Period
from app.db.session import get_session
from app.domain.periods import format_period
from app.schemas import PeriodOut

router = APIRouter(tags=["periods"])


@router.get("/periods", response_model=list[PeriodOut])
def list_periods(session: Session = Depends(get_session)) -> list[PeriodOut]:
    rows = session.exec(select(Period).order_by(col(Period.period_key))).all()
    return [
        PeriodOut(
            period_key=p.period_key,
            label=format_period(p.period_key),
            year=p.year,
            month_num=p.month_num,
            fiscal_year=p.fiscal_year,
            fiscal_quarter=p.fiscal_quarter,
            is_closed=p.is_closed,
        )
        for p in rows
    ]
