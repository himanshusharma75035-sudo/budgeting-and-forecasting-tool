"""Budget generation endpoint — dispatches to the four engines (DESIGN.md 2)."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db.models import BudgetVersion
from app.db.session import get_session
from app.domain.budgeting import (
    Activity,
    DecisionPackage,
    IncrementalLine,
    Initiative,
    activity_based_budget,
    incremental_budget,
    value_proposition_budget,
    zero_based_budget,
)
from app.domain.enums import BudgetMethod
from app.schemas import BudgetLineOut, BudgetRunRequest, BudgetRunResponse

router = APIRouter(tags=["budgets"])


def _require(value, name: str):  # noqa: ANN001
    if value is None:
        raise HTTPException(422, f"method requires '{name}'")
    return value


def _run_engine(req: BudgetRunRequest) -> tuple[list[BudgetLineOut], Decimal, list[str]]:
    notes: list[str] = []
    if req.method == BudgetMethod.INCREMENTAL:
        lines_in = _require(req.incremental_lines, "incremental_lines")
        inc = incremental_budget(
            [IncrementalLine(x.account_code, x.prior_actual, x.growth_pct, x.one_off) for x in lines_in]
        )
        lines = [BudgetLineOut(account_code=b.account_code, amount=b.amount) for b in inc]
        total = sum((b.amount for b in inc), Decimal("0"))
        return lines, total, notes

    if req.method == BudgetMethod.ACTIVITY_BASED:
        acts = _require(req.activities, "activities")
        abb = activity_based_budget(
            [Activity(a.name, a.prior_cost_pool, a.prior_driver_units, a.forecast_driver_volume) for a in acts],
            fixed_costs=req.fixed_costs,
        )
        lines = [BudgetLineOut(name=b.name, amount=b.amount) for b in abb.lines]
        if req.fixed_costs:
            lines.append(BudgetLineOut(name="Fixed costs", amount=req.fixed_costs))
        return lines, abb.total, notes

    if req.method == BudgetMethod.VALUE_PROPOSITION:
        inits = _require(req.initiatives, "initiatives")
        cap = _require(req.cap, "cap")
        cost_by_name = {i.name: i.cost for i in inits}
        decision = value_proposition_budget(
            [Initiative(i.name, i.cost, i.value_score) for i in inits], cap, optimal=req.optimal
        )
        lines = [BudgetLineOut(name=n, amount=cost_by_name[n]) for n in decision.funded]
        notes.append(f"Deferred: {', '.join(decision.deferred) or 'none'}")
        notes.append(f"Funded value={decision.total_value}, slack={decision.slack}")
        return lines, decision.total_cost, notes

    if req.method == BudgetMethod.ZERO_BASED:
        pkgs = _require(req.packages, "packages")
        funds = _require(req.total_funds, "total_funds")
        cost_by_name = {p.name: p.cost for p in pkgs}
        zbb = zero_based_budget(
            [DecisionPackage(p.name, p.cost, p.benefit) for p in pkgs], funds
        )
        lines = [BudgetLineOut(name=n, amount=cost_by_name[n]) for n in zbb.funded]
        notes.append(f"Ranking: {', '.join(zbb.ranking)}")
        notes.append(f"Unfunded: {', '.join(zbb.unfunded) or 'none'}, remaining={zbb.remaining_funds}")
        return lines, zbb.total_cost, notes

    raise HTTPException(422, f"unsupported method {req.method}")


@router.post("/budgets/run", response_model=BudgetRunResponse)
def run_budget(req: BudgetRunRequest, session: Session = Depends(get_session)) -> BudgetRunResponse:
    lines, total, notes = _run_engine(req)
    version = BudgetVersion(
        version_name=req.version_name,
        fiscal_year=req.fiscal_year,
        method=req.method,
        volume_mode=req.volume_mode,
        cadence=req.cadence,
    )
    session.add(version)
    session.commit()
    session.refresh(version)
    return BudgetRunResponse(
        budget_version_id=version.budget_version_id,
        method=req.method,
        lines=lines,
        total=total,
        notes=notes,
    )
