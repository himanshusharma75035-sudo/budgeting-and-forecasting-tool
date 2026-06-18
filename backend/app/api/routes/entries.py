"""Fact entries: the long store + single-cell upsert for the manual grid."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, col, select

from app.db.models import Account, Entry
from app.db.session import get_session
from app.domain.enums import Scenario
from app.domain.money import from_minor, to_minor
from app.domain.periods import format_period, parse_period
from app.schemas import CellUpsert, EntryOut
from app.services.lookup import account_by_code, ensure_period, resolve_dim_id

router = APIRouter(tags=["entries"])


@router.get("/entries", response_model=list[EntryOut])
def list_entries(
    session: Session = Depends(get_session),
    scenario: Scenario = Scenario.ACTUAL,
    account_code: str | None = None,
    budget_version_id: int | None = None,
    forecast_run_id: int | None = None,
    period_from: str | None = Query(None, description="YYYY-MM"),
    period_to: str | None = Query(None, description="YYYY-MM"),
) -> list[EntryOut]:
    stmt = select(Entry, Account).join(Account).where(Entry.scenario == scenario)
    if account_code:
        stmt = stmt.where(Account.account_code == account_code)
    if budget_version_id is not None:
        stmt = stmt.where(Entry.budget_version_id == budget_version_id)
    if forecast_run_id is not None:
        stmt = stmt.where(Entry.forecast_run_id == forecast_run_id)
    if period_from:
        stmt = stmt.where(Entry.period_key >= parse_period(period_from))
    if period_to:
        stmt = stmt.where(Entry.period_key <= parse_period(period_to))
    stmt = stmt.order_by(col(Account.account_code), col(Entry.period_key))
    out: list[EntryOut] = []
    for entry, acct in session.exec(stmt).all():
        out.append(
            EntryOut(
                account_code=acct.account_code,
                period=format_period(entry.period_key),
                scenario=entry.scenario,
                amount=from_minor(entry.amount_minor, entry.minor_unit_scale),
            )
        )
    return out


@router.put("/entries/cell", response_model=EntryOut | None)
def upsert_cell(payload: CellUpsert, session: Session = Depends(get_session)) -> EntryOut | None:
    acct = account_by_code(session, payload.account_code)
    if acct is None:
        raise HTTPException(404, f"unknown account_code '{payload.account_code}'")
    if not acct.is_postable:
        raise HTTPException(422, f"account '{payload.account_code}' is a roll-up node, not postable")
    assert acct.account_id is not None  # persisted account always has an id
    period_key = parse_period(payload.period)
    ensure_period(session, period_key)

    dim_ids: dict[str, int] = {}
    for field, code in [
        ("entity_code", payload.entity_code),
        ("department_code", payload.department_code),
        ("project_code", payload.project_code),
        ("region_code", payload.region_code),
    ]:
        rid = resolve_dim_id(session, field, code)
        if rid is None:
            raise HTTPException(422, f"unknown {field} '{code}'")
        dim_ids[field] = rid

    existing = session.exec(
        select(Entry).where(
            Entry.account_id == acct.account_id,
            Entry.period_key == period_key,
            Entry.entity_id == dim_ids["entity_code"],
            Entry.department_id == dim_ids["department_code"],
            Entry.project_id == dim_ids["project_code"],
            Entry.region_id == dim_ids["region_code"],
            Entry.scenario == payload.scenario,
            Entry.budget_version_id == payload.budget_version_id,
            Entry.forecast_run_id == payload.forecast_run_id,
        )
    ).first()

    if payload.amount is None:  # clearing the cell deletes the row
        if existing:
            session.delete(existing)
            session.commit()
        return None

    minor = to_minor(payload.amount)
    now = datetime.now(UTC)
    if existing:
        existing.amount_minor = minor
        existing.updated_at = now
        session.add(existing)
    else:
        existing = Entry(
            account_id=acct.account_id,
            period_key=period_key,
            entity_id=dim_ids["entity_code"],
            department_id=dim_ids["department_code"],
            project_id=dim_ids["project_code"],
            region_id=dim_ids["region_code"],
            scenario=payload.scenario,
            budget_version_id=payload.budget_version_id,
            forecast_run_id=payload.forecast_run_id,
            amount_minor=minor,
            source="manual",
        )
        session.add(existing)
    session.commit()
    return EntryOut(
        account_code=acct.account_code,
        period=payload.period,
        scenario=payload.scenario,
        amount=payload.amount,
    )
