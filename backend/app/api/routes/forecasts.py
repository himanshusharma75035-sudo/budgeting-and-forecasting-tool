"""Autonomous forecasting endpoint (DESIGN.md 3)."""

from __future__ import annotations

import math

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, col, select

from app.db.models import Entry, ForecastRun
from app.db.session import get_session
from app.domain.enums import Scenario
from app.domain.forecasting import auto_forecast
from app.domain.money import from_minor
from app.schemas import ForecastRunRequest, ForecastRunResponse, ModelScoreOut
from app.services.lookup import account_by_code

router = APIRouter(tags=["forecasts"])


def _finite(value: float | None) -> float | None:
    """Map NaN/inf to None so the response is valid JSON."""
    if value is None or not math.isfinite(value):
        return None
    return value


def _history_from_db(session: Session, account_code: str) -> list[float]:
    acct = account_by_code(session, account_code)
    if acct is None:
        raise HTTPException(404, f"unknown account_code '{account_code}'")
    rows = session.exec(
        select(Entry)
        .where(Entry.account_id == acct.account_id, Entry.scenario == Scenario.ACTUAL)
        .order_by(col(Entry.period_key))
    ).all()
    return [float(from_minor(r.amount_minor, r.minor_unit_scale)) for r in rows]


@router.post("/forecasts/run", response_model=ForecastRunResponse)
def run_forecast(req: ForecastRunRequest, session: Session = Depends(get_session)) -> ForecastRunResponse:
    history = req.history if req.history is not None else _history_from_db(session, req.account_code)
    if len(history) < 2:
        raise HTTPException(422, "need at least 2 historical points to forecast")

    result = auto_forecast(
        history,
        h=req.horizon,
        freq=req.freq,
        levels=tuple(req.levels),
        allow_seasonal=req.allow_seasonal,
        model_override=req.model_override,
    )

    run_id: int | None = None
    if req.persist:
        run = ForecastRun(
            run_label=req.run_label or f"{req.account_code}-forecast",
            method="auto",
            selected_model=result.model,
            cv_mase=_finite(next((s.mase for s in result.scoreboard if s.model == result.model), None)),
            horizon=req.horizon,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.forecast_run_id

    return ForecastRunResponse(
        forecast_run_id=run_id,
        account_code=req.account_code,
        selected_model=result.model,
        horizon=req.horizon,
        seasonal_period=result.seasonal_period,
        point=result.point,
        lower=result.lower,
        upper=result.upper,
        scoreboard=[
            ModelScoreOut(model=s.model, mase=_finite(s.mase), rmse=_finite(s.rmse), mae=_finite(s.mae))
            for s in result.scoreboard
        ],
        notes=result.notes,
    )
