"""Pydantic request/response DTOs for the API layer.

These are deliberately decoupled from both the ORM models and the domain dataclasses; routes
map between them. Amounts cross the API as major-unit decimals (strings/numbers); they are
converted to integer minor units only at the persistence boundary.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, PlainSerializer

from app.domain.enums import (
    AccountType,
    BudgetMethod,
    Cadence,
    DriverKind,
    Scenario,
    VarianceKind,
    VolumeMode,
)

# A money amount: carried internally as exact Decimal, emitted to JSON as a number (not a string,
# which is Pydantic's default for Decimal) so the frontend can do arithmetic and chart it.
Money = Annotated[Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")]

# --- accounts / reference --------------------------------------------------


class AccountIn(BaseModel):
    account_code: str
    account_name: str
    account_type: AccountType
    account_category: str | None = None
    parent_account_id: int | None = None
    is_postable: bool = True
    sort_order: int | None = None


class AccountOut(AccountIn):
    account_id: int
    normal_balance: str
    sign_factor: int
    is_active: bool


class PeriodOut(BaseModel):
    period_key: int
    label: str
    year: int
    month_num: int
    fiscal_year: int
    fiscal_quarter: int
    is_closed: bool


# --- entries / manual grid -------------------------------------------------


class CellUpsert(BaseModel):
    account_code: str
    period: str  # YYYY-MM
    scenario: Scenario = Scenario.ACTUAL
    amount: Decimal | None = None  # None clears the cell
    entity_code: str = "ALL"
    department_code: str = "UNALLOC"
    project_code: str = "NONE"
    region_code: str = "ALL"
    budget_version_id: int | None = None
    forecast_run_id: int | None = None


class EntryOut(BaseModel):
    account_code: str
    period: str
    scenario: Scenario
    amount: Money  # exact Decimal internally; serialized to a JSON number


# --- budgeting -------------------------------------------------------------


class IncrementalLineIn(BaseModel):
    account_code: str
    prior_actual: Decimal
    growth_pct: Decimal = Decimal("0")  # 0.08 == +8%
    one_off: Decimal = Decimal("0")


class ActivityIn(BaseModel):
    name: str
    prior_cost_pool: Decimal
    prior_driver_units: Decimal
    forecast_driver_volume: Decimal


class InitiativeIn(BaseModel):
    name: str
    cost: Decimal
    value_score: Decimal


class DecisionPackageIn(BaseModel):
    name: str
    cost: Decimal
    benefit: Decimal


class BudgetRunRequest(BaseModel):
    method: BudgetMethod
    version_name: str
    fiscal_year: int
    volume_mode: VolumeMode = VolumeMode.STATIC
    cadence: Cadence = Cadence.PERIODIC
    # method-specific payloads (only the relevant one is required)
    incremental_lines: list[IncrementalLineIn] | None = None
    activities: list[ActivityIn] | None = None
    fixed_costs: Decimal = Decimal("0")
    initiatives: list[InitiativeIn] | None = None
    packages: list[DecisionPackageIn] | None = None
    cap: Decimal | None = None
    total_funds: Decimal | None = None
    optimal: bool = False


class BudgetLineOut(BaseModel):
    account_code: str | None = None
    name: str | None = None
    amount: Money


class BudgetRunResponse(BaseModel):
    budget_version_id: int | None = None
    method: BudgetMethod
    lines: list[BudgetLineOut]
    total: Money
    notes: list[str] = Field(default_factory=list)


# --- forecasting -----------------------------------------------------------


class ForecastRunRequest(BaseModel):
    account_code: str
    history: list[float] | None = None  # optional inline series; else read from DB actuals
    horizon: int = 12
    freq: str = "M"
    levels: list[int] = Field(default_factory=lambda: [80, 95])
    allow_seasonal: bool | None = None
    model_override: str | None = None
    persist: bool = False
    run_label: str | None = None


class ModelScoreOut(BaseModel):
    model: str
    mase: float | None = None
    rmse: float | None = None
    mae: float | None = None


class ForecastRunResponse(BaseModel):
    forecast_run_id: int | None = None
    account_code: str
    selected_model: str
    horizon: int
    seasonal_period: int
    point: list[float]
    lower: dict[int, list[float]]
    upper: dict[int, list[float]]
    scoreboard: list[ModelScoreOut]
    notes: list[str] = Field(default_factory=list)


# --- variance --------------------------------------------------------------


class VarianceComputeRequest(BaseModel):
    base_scenario: Scenario = Scenario.ACTUAL
    compare_scenario: Scenario = Scenario.BUDGET
    budget_version_id: int | None = None
    forecast_run_id: int | None = None
    period_from: str | None = None
    period_to: str | None = None
    pct_threshold: float = 0.10
    abs_threshold: Decimal = Decimal("0")


class VarianceRowOut(BaseModel):
    account_code: str
    period: str
    account_type: AccountType
    actual: Money
    comparison: Money
    variance: Money
    favorable_variance: Money
    variance_pct: float | None
    status: str
    is_material: bool
    variance_kind: VarianceKind = VarianceKind.BUDGET_VS_ACTUAL


class BridgeStepOut(BaseModel):
    label: str
    delta: Money


class BridgeOut(BaseModel):
    start: Money
    steps: list[BridgeStepOut]
    end: Money


class InsightDriverOut(BaseModel):
    code: str
    label: str
    category: str | None = None
    favorable_variance: Money
    actual: Money
    comparison: Money
    is_material: bool


class VarianceInsightOut(BaseModel):
    net_favorable: Money
    status: str
    favorable_total: Money
    unfavorable_total: Money
    top_favorable: list[InsightDriverOut]
    top_unfavorable: list[InsightDriverOut]
    by_category: list[InsightDriverOut]
    material: list[InsightDriverOut]
    narrative: str
    ai_generated: bool = False


# --- drivers (driver-based modeling) ---------------------------------------


class DriverIn(BaseModel):
    code: str
    name: str
    kind: DriverKind
    formula: str | None = None
    values: dict[str, Decimal] = Field(default_factory=dict)  # period (YYYY-MM) -> value
    account_code: str | None = None
    unit: str | None = None


class DriverModelRequest(BaseModel):
    periods: list[str]
    drivers: list[DriverIn]


class DriverSeriesOut(BaseModel):
    code: str
    name: str
    kind: DriverKind
    unit: str | None = None
    account_code: str | None = None
    points: list[Money]


class AccountLineOut(BaseModel):
    account_code: str
    points: list[Money]
    total: Money


class DriverEvalResponse(BaseModel):
    periods: list[str]
    series: list[DriverSeriesOut]
    account_lines: list[AccountLineOut]
    notes: list[str] = Field(default_factory=list)


class UploadReport(BaseModel):
    layout: str
    rows_total: int
    rows_ok: int
    rows_rejected: int
    inserted: int
    errors: list[dict] = Field(default_factory=list)
