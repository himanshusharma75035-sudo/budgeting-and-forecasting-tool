"""Reference-data lookups (codes -> ids) shared by the entries and upload services."""

from __future__ import annotations

from sqlmodel import Session, select

from app.config import settings
from app.db.models import Account, DimDepartment, DimEntity, DimProject, DimRegion, Period
from app.domain.periods import fiscal_attrs, month_bounds, month_name, split_period_key

_DIM_BY_FIELD = {
    "entity_code": DimEntity,
    "department_code": DimDepartment,
    "project_code": DimProject,
    "region_code": DimRegion,
}
_DIM_PK = {
    DimEntity: "entity_id",
    DimDepartment: "department_id",
    DimProject: "project_id",
    DimRegion: "region_id",
}


def account_by_code(session: Session, code: str) -> Account | None:
    return session.exec(select(Account).where(Account.account_code == code)).first()


def account_map(session: Session) -> dict[str, Account]:
    return {a.account_code: a for a in session.exec(select(Account)).all()}


def known_account_codes(session: Session) -> set[str]:
    return {a.account_code for a in session.exec(select(Account)).all()}


def known_dim_codes(session: Session) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for field, model in _DIM_BY_FIELD.items():
        out[field] = {d.code for d in session.exec(select(model)).all()}
    return out


def resolve_dim_id(session: Session, field: str, code: str) -> int | None:
    """Map a dimension code to its id; returns None if unknown."""
    model = _DIM_BY_FIELD[field]
    pk = _DIM_PK[model]
    row = session.exec(select(model).where(model.code == code)).first()
    return getattr(row, pk) if row else None


def ensure_period(session: Session, period_key: int) -> None:
    """Create the period row (with fiscal attributes) if it doesn't exist yet, then flush
    so a subsequent entry insert satisfies the foreign key."""
    if session.get(Period, period_key) is not None:
        return
    year, month = split_period_key(period_key)
    fa = fiscal_attrs(period_key, settings.fiscal_year_start_month)
    start, end = month_bounds(period_key)
    session.add(
        Period(
            period_key=period_key,
            year=year,
            month_num=month,
            month_name=month_name(period_key),
            quarter=fa["quarter"],
            period_start_date=start,
            period_end_date=end,
            fiscal_year=fa["fiscal_year"],
            fiscal_quarter=fa["fiscal_quarter"],
            fiscal_period_num=fa["fiscal_period_num"],
        )
    )
    session.flush()
