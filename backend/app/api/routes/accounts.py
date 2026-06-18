"""Chart-of-accounts and dimension reference endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, col, select

from app.db.models import Account, DimDepartment, DimEntity, DimProject, DimRegion
from app.db.session import get_session
from app.domain.enums import normal_balance, sign_factor
from app.schemas import AccountIn, AccountOut

router = APIRouter(tags=["accounts"])


def _to_out(a: Account) -> AccountOut:
    return AccountOut(
        account_id=a.account_id or 0,
        account_code=a.account_code,
        account_name=a.account_name,
        account_type=a.account_type,
        account_category=a.account_category,
        parent_account_id=a.parent_account_id,
        is_postable=a.is_postable,
        sort_order=a.sort_order,
        normal_balance=a.normal_balance.value,
        sign_factor=a.sign_factor,
        is_active=a.is_active,
    )


@router.get("/accounts", response_model=list[AccountOut])
def list_accounts(session: Session = Depends(get_session)) -> list[AccountOut]:
    rows = session.exec(
        select(Account).order_by(col(Account.sort_order), col(Account.account_code))
    ).all()
    return [_to_out(a) for a in rows]


@router.post("/accounts", response_model=AccountOut, status_code=201)
def create_account(payload: AccountIn, session: Session = Depends(get_session)) -> AccountOut:
    if session.exec(select(Account).where(Account.account_code == payload.account_code)).first():
        raise HTTPException(409, f"account_code '{payload.account_code}' already exists")
    acct = Account(
        account_code=payload.account_code,
        account_name=payload.account_name,
        account_type=payload.account_type,
        account_category=payload.account_category,
        parent_account_id=payload.parent_account_id,
        is_postable=payload.is_postable,
        sort_order=payload.sort_order,
        normal_balance=normal_balance(payload.account_type),
        sign_factor=sign_factor(payload.account_type),
    )
    session.add(acct)
    session.commit()
    session.refresh(acct)
    return _to_out(acct)


@router.get("/dimensions/{kind}")
def list_dimension(kind: str, session: Session = Depends(get_session)) -> list[dict]:
    models = {
        "entity": DimEntity,
        "department": DimDepartment,
        "project": DimProject,
        "region": DimRegion,
    }
    model = models.get(kind)
    if model is None:
        raise HTTPException(404, f"unknown dimension '{kind}' (entity|department|project|region)")
    rows = session.exec(select(model)).all()
    return [{"code": r.code, "name": r.name, "is_active": r.is_active} for r in rows]
