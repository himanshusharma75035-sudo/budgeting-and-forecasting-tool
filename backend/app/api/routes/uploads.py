"""Upload ingestion + template download (DESIGN.md 5.4)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlmodel import Session, col, select

from app.db.models import Account, Entry, Period
from app.db.session import get_session
from app.domain.enums import Scenario
from app.domain.ingestion import (
    detect_layout,
    long_dataframe_to_records,
    pivot_wide_to_long,
    read_table,
    validate_long,
    validate_wide,
    wide_template_csv,
)
from app.domain.money import to_minor
from app.domain.periods import format_period
from app.schemas import UploadReport
from app.services.lookup import (
    account_map,
    ensure_period,
    known_account_codes,
    known_dim_codes,
    resolve_dim_id,
)

router = APIRouter(tags=["uploads"])


@router.post("/uploads", response_model=UploadReport)
async def upload(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    scenario: Scenario = Scenario.ACTUAL,
    budget_version_id: int | None = None,
    forecast_run_id: int | None = None,
) -> UploadReport:
    raw = await file.read()
    df = read_table(raw, file.filename or "upload.csv")
    layout = detect_layout(df)

    acct_codes = known_account_codes(session)
    dim_codes = known_dim_codes(session)
    if layout == "WIDE":
        report = validate_wide(df, acct_codes, dim_codes)
        records = pivot_wide_to_long(df) if report.ok else []
    else:
        report = validate_long(df, acct_codes, dim_codes)
        records = long_dataframe_to_records(df) if report.ok else []

    inserted = 0
    if report.ok:
        amap = account_map(session)
        now = datetime.now(UTC)
        for rec in records:
            acct = amap.get(rec.account_code)
            if acct is None or acct.account_id is None:
                continue
            ensure_period(session, rec.period_key)
            ids = {
                "entity_id": resolve_dim_id(session, "entity_code", rec.entity_code) or 0,
                "department_id": resolve_dim_id(session, "department_code", rec.department_code) or 0,
                "project_id": resolve_dim_id(session, "project_code", rec.project_code) or 0,
                "region_id": resolve_dim_id(session, "region_code", rec.region_code) or 0,
            }
            existing = session.exec(
                select(Entry).where(
                    Entry.account_id == acct.account_id,
                    Entry.period_key == rec.period_key,
                    Entry.entity_id == ids["entity_id"],
                    Entry.department_id == ids["department_id"],
                    Entry.project_id == ids["project_id"],
                    Entry.region_id == ids["region_id"],
                    Entry.scenario == scenario,
                    Entry.budget_version_id == budget_version_id,
                    Entry.forecast_run_id == forecast_run_id,
                )
            ).first()
            minor = to_minor(rec.amount)
            if existing:
                existing.amount_minor = minor
                existing.updated_at = now
                session.add(existing)
            else:
                session.add(
                    Entry(
                        account_id=acct.account_id,
                        period_key=rec.period_key,
                        scenario=scenario,
                        budget_version_id=budget_version_id,
                        forecast_run_id=forecast_run_id,
                        amount_minor=minor,
                        currency=rec.currency,
                        source=f"upload:{file.filename}",
                        **ids,
                    )
                )
            inserted += 1
        session.commit()

    rejected = report.rows_total - report.rows_ok
    return UploadReport(
        layout=layout,
        rows_total=report.rows_total,
        rows_ok=report.rows_ok,
        rows_rejected=rejected,
        inserted=inserted,
        errors=[{"row": e.row, "field": e.field, "message": e.message} for e in report.errors],
    )


@router.get("/templates/{scenario}")
def download_template(
    scenario: Scenario,
    session: Session = Depends(get_session),
    n_periods: int = Query(12, ge=1, le=36),
) -> Response:
    accounts = [
        (a.account_code, a.account_name)
        for a in session.exec(
            select(Account).where(col(Account.is_postable)).order_by(col(Account.account_code))
        ).all()
    ]
    period_keys = [
        p.period_key for p in session.exec(select(Period).order_by(col(Period.period_key))).all()
    ][:n_periods]
    period_labels = [format_period(k) for k in period_keys] or ["2026-01", "2026-02", "2026-03"]
    csv_text = wide_template_csv(accounts, period_labels)
    filename = f"{scenario.value.lower()}_wide_template.csv"
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
