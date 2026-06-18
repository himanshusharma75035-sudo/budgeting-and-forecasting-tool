"""SQLModel ORM models — the long/tidy fact store described in DESIGN.md section 5.

Money is stored as integer minor units (``amount_minor``). The fact table ``entries`` holds
ACTUAL / BUDGET / FORECAST rows distinguished by ``scenario`` (+ version/run id).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from app.domain.enums import (
    AccountType,
    BalanceType,
    BudgetMethod,
    BudgetStatus,
    Cadence,
    NormalBalance,
    Scenario,
    StatementSection,
    VarianceKind,
    VarianceStatus,
    VolumeMode,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


# --- reference data --------------------------------------------------------


class Account(SQLModel, table=True):
    __tablename__ = "accounts"

    account_id: int | None = Field(default=None, primary_key=True)
    account_code: str = Field(index=True, unique=True)
    account_name: str
    account_type: AccountType
    statement_section: StatementSection = StatementSection.PL
    account_category: str | None = None
    parent_account_id: int | None = Field(default=None, foreign_key="accounts.account_id")
    normal_balance: NormalBalance
    sign_factor: int = 1  # +1 revenue/income, -1 cost/expense (P&L)
    balance_type: BalanceType = BalanceType.FLOW
    is_postable: bool = True
    sort_order: int | None = None
    is_active: bool = True


class _Dimension(SQLModel):
    code: str = Field(index=True, unique=True)
    name: str
    is_active: bool = True


class DimEntity(_Dimension, table=True):
    __tablename__ = "dim_entity"
    entity_id: int | None = Field(default=None, primary_key=True)
    currency: str = "INR"
    parent_id: int | None = Field(default=None, foreign_key="dim_entity.entity_id")


class DimDepartment(_Dimension, table=True):
    __tablename__ = "dim_department"
    department_id: int | None = Field(default=None, primary_key=True)
    parent_id: int | None = Field(default=None, foreign_key="dim_department.department_id")


class DimProject(_Dimension, table=True):
    __tablename__ = "dim_project"
    project_id: int | None = Field(default=None, primary_key=True)


class DimRegion(_Dimension, table=True):
    __tablename__ = "dim_region"
    region_id: int | None = Field(default=None, primary_key=True)


class Period(SQLModel, table=True):
    __tablename__ = "periods"

    period_key: int = Field(primary_key=True)  # smart key YYYYMM
    year: int
    month_num: int
    month_name: str | None = None
    quarter: int | None = None
    period_start_date: str
    period_end_date: str
    fiscal_year: int
    fiscal_quarter: int
    fiscal_period_num: int
    is_closed: bool = False


# --- scenario containers ---------------------------------------------------


class BudgetVersion(SQLModel, table=True):
    __tablename__ = "budget_versions"

    budget_version_id: int | None = Field(default=None, primary_key=True)
    version_name: str
    fiscal_year: int
    method: BudgetMethod | None = None
    volume_mode: VolumeMode | None = None
    cadence: Cadence | None = None
    status: BudgetStatus = BudgetStatus.DRAFT
    is_active: bool = False
    assumptions_json: str | None = None
    created_by: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)


class ForecastRun(SQLModel, table=True):
    __tablename__ = "forecast_runs"

    forecast_run_id: int | None = Field(default=None, primary_key=True)
    run_label: str
    as_of_period_key: int | None = Field(default=None, foreign_key="periods.period_key")
    method: str | None = None
    selected_model: str | None = None
    cv_mase: float | None = None
    horizon: int | None = None
    assumptions_json: str | None = None
    created_by: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)


# --- facts -----------------------------------------------------------------


class Entry(SQLModel, table=True):
    __tablename__ = "entries"

    entry_id: int | None = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="accounts.account_id", index=True)
    period_key: int = Field(foreign_key="periods.period_key", index=True)
    entity_id: int = Field(default=0, foreign_key="dim_entity.entity_id")
    department_id: int = Field(default=0, foreign_key="dim_department.department_id")
    project_id: int = Field(default=0, foreign_key="dim_project.project_id")
    region_id: int = Field(default=0, foreign_key="dim_region.region_id")
    scenario: Scenario = Field(index=True)
    budget_version_id: int | None = Field(
        default=None, foreign_key="budget_versions.budget_version_id"
    )
    forecast_run_id: int | None = Field(default=None, foreign_key="forecast_runs.forecast_run_id")
    amount_minor: int
    currency: str = "INR"
    minor_unit_scale: int = 2
    source: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class VarianceResult(SQLModel, table=True):
    __tablename__ = "variance_results"

    variance_id: int | None = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="accounts.account_id", index=True)
    period_key: int = Field(foreign_key="periods.period_key", index=True)
    entity_id: int = 0
    department_id: int = 0
    project_id: int = 0
    region_id: int = 0
    base_scenario: Scenario
    compare_scenario: Scenario
    budget_version_id: int | None = None
    forecast_run_id: int | None = None
    variance_kind: VarianceKind = VarianceKind.BUDGET_VS_ACTUAL
    actual_minor: int = 0
    comparison_minor: int = 0
    variance_minor: int = 0
    favorable_variance_minor: int = 0
    variance_pct: float | None = None
    variance_status: VarianceStatus = VarianceStatus.NEUTRAL
    is_material: bool = False
    computed_at: datetime = Field(default_factory=_utcnow)


class ChangeLog(SQLModel, table=True):
    __tablename__ = "change_log"

    change_id: int | None = Field(default=None, primary_key=True)
    table_name: str
    row_key: str
    field: str
    old_value: str | None = None
    new_value: str | None = None
    changed_by: str | None = None
    changed_at: datetime = Field(default_factory=_utcnow)
