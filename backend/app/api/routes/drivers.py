"""Driver-based modeling endpoint (roadmap 0.2).

Evaluates a driver model — inputs + formulas over periods — into per-driver series and per-account
lines. Stateless compute (mirrors ``/budgets/run``'s inline-payload style); persistence of the
resulting lines as scenario entries is a planned follow-up.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.domain.drivers import Driver, DriverError, FormulaError, evaluate_model
from app.schemas import (
    AccountLineOut,
    DriverEvalResponse,
    DriverModelRequest,
    DriverSeriesOut,
)

router = APIRouter(tags=["drivers"])


@router.post("/drivers/evaluate", response_model=DriverEvalResponse)
def evaluate_drivers(req: DriverModelRequest) -> DriverEvalResponse:
    if not req.periods:
        raise HTTPException(422, "at least one period is required")
    drivers = [
        Driver(
            code=d.code,
            name=d.name,
            kind=d.kind,
            formula=d.formula,
            values=d.values,
            account_code=d.account_code,
            unit=d.unit,
        )
        for d in req.drivers
    ]
    try:
        result = evaluate_model(drivers, req.periods)
    except (DriverError, FormulaError) as e:
        raise HTTPException(422, str(e)) from e

    return DriverEvalResponse(
        periods=result.periods,
        series=[
            DriverSeriesOut(
                code=s.code,
                name=s.name,
                kind=s.kind,
                unit=s.unit,
                account_code=s.account_code,
                points=s.points,
            )
            for s in result.series
        ],
        account_lines=[
            AccountLineOut(account_code=a.account_code, points=a.points, total=a.total)
            for a in result.account_lines
        ],
        notes=[f"{len(result.series)} drivers evaluated over {len(result.periods)} periods"],
    )
