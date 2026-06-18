// Shared API response/request types mirroring the FastAPI backend (all routes under /api).

export interface AccountOut {
  account_id: number;
  account_code: string;
  account_name: string;
  account_type: string;
  normal_balance: string;
  sign_factor: number;
  is_postable: boolean;
  is_active: boolean;
}

export interface PeriodOut {
  period_key: number;
  label: string;
  year: number;
  month_num: number;
  fiscal_year: number;
  fiscal_quarter: number;
  is_closed: boolean;
}

export interface EntryOut {
  account_code: string;
  period: string; // YYYY-MM
  scenario: string;
  amount: number;
}

export interface UploadReport {
  layout: string;
  rows_total: number;
  rows_ok: number;
  rows_rejected: number;
  inserted: number;
  errors: Record<string, unknown>[];
}

// ---- Budgets ----

export type BudgetMethod = "INCREMENTAL" | "ACTIVITY_BASED" | "VALUE_PROPOSITION" | "ZERO_BASED";

export interface IncrementalLineInput {
  account_code: string;
  prior_actual: number;
  growth_pct: number;
  one_off: number;
}
export interface ActivityInput {
  name: string;
  prior_cost_pool: number;
  prior_driver_units: number;
  forecast_driver_volume: number;
}
export interface InitiativeInput {
  name: string;
  cost: number;
  value_score: number;
}
export interface DecisionPackageInput {
  name: string;
  cost: number;
  benefit: number;
}

export interface BudgetRunRequest {
  method: BudgetMethod;
  version_name: string;
  fiscal_year: number;
  volume_mode?: string;
  cadence?: string;
  incremental_lines?: IncrementalLineInput[];
  activities?: ActivityInput[];
  fixed_costs?: number;
  initiatives?: InitiativeInput[];
  packages?: DecisionPackageInput[];
  cap?: number;
  total_funds?: number;
  optimal?: boolean;
}

export interface BudgetLineOut {
  account_code?: string | null;
  name?: string | null;
  amount: number;
}

export interface BudgetRunResponse {
  budget_version_id: number | null;
  method: string;
  lines: BudgetLineOut[];
  total: number;
  notes: string[];
}

// ---- Forecasts ----

export interface ForecastRunRequest {
  account_code: string;
  history?: number[];
  horizon: number;
  levels: number[];
  model_override?: string | null;
}

export interface ForecastScoreboardEntry {
  model: string;
  mase: number | null;
  rmse: number | null;
  mae: number | null;
}

export interface ForecastRunResponse {
  forecast_run_id: number | null;
  account_code: string;
  selected_model: string;
  horizon: number;
  seasonal_period: number;
  point: number[];
  lower: Record<string, number[]>;
  upper: Record<string, number[]>;
  scoreboard: ForecastScoreboardEntry[];
  notes: string[];
}

// ---- Variance ----

export interface VarianceComputeRequest {
  base_scenario: string;
  compare_scenario: string;
  budget_version_id?: number | null;
  forecast_run_id?: number | null;
  period_from?: string | null;
  period_to?: string | null;
  pct_threshold?: number;
  abs_threshold?: number;
}

export interface VarianceRowOut {
  account_code: string;
  period: string;
  account_type: string;
  actual: number;
  comparison: number;
  variance: number;
  favorable_variance: number;
  variance_pct: number | null;
  status: string;
  is_material: boolean;
  variance_kind: string;
}

export interface BridgeStepOut {
  label: string;
  delta: number;
}

export interface BridgeOut {
  start: number;
  steps: BridgeStepOut[];
  end: number;
}
