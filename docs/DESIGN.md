# Build Brief: Open-Source Budgeting & Forecasting Tool

**Document status:** Implementation-ready build brief
**Date:** 2026-06-18
**Stack (fixed):** FastAPI (Python) + React/TypeScript, local single-user, SQLite, OSI-permissive dependencies only.

---

## 1. Executive Summary & Product Scope

### 1.1 What we are building

A **local-first, single-user desktop-grade web application** for corporate FP&A that combines three capabilities that do not currently coexist in any open-source tool:

1. **Four formal corporate budgeting methods** (Incremental, Activity-Based, Value-Proposition, Zero-Based) as selectable derivation engines, wrapped by orthogonal Static/Flexible and Periodic/Rolling modifiers.
2. **Autonomous statistical forecasting** (auto-selected ARIMA/SARIMA, ETS/Holt-Winters, Theta/CES, Prophet, plus transparent classic FP&A methods) with rolling-origin backtesting, MASE-based model selection, and prediction intervals.
3. **Rigorous variance analysis** (budget-vs-actual plus full price/volume/mix/efficiency decomposition) with a sign-safe favorable/unfavorable engine and waterfall visualization.

### 1.2 Why this is a genuine gap

The OSS landscape splits into personal-finance budgeting apps (Actual Budget — MIT, envelope budgeting, great import UX, **no** forecasting/variance), double-entry accounting (GnuCash, Firefly III — budget-vs-spent but **no** statistical forecasting), and plain-text accounting (hledger — the only tool with both `--budget` variance and `--forecast`, but both are **deterministic, hand-authored** rule projections, **not** statistical models). No mature open-source corporate FP&A tool exists that unifies all four budgeting methods + autonomous statistical forecasting + corporate variance analysis in one local tool. That intersection is our wedge.

### 1.3 Product principles

- **Local-first, no mandatory cloud.** One SQLite file per workspace. (Maybe Finance's VC/cloud-dependent archival in 2025 is the cautionary tale; Actual Budget's local-file model is the pattern to emulate.)
- **Permissive license.** The distributable is MIT/BSD/Apache; we deliberately avoid the AGPL posture of Firefly III / Lago / OpenBB so the tool can be embedded and adopted freely.
- **Autonomous by default, overridable always.** Forecasting auto-selects the best model per series, but the user can pin a model. Budgets auto-derive from actuals/drivers, but every cell is editable.
- **Borrow proven UX:** Actual Budget's multi-format importers; hledger's unified budget-goal-as-forecast-seed concept (but replace its hand-authored amounts with statistically forecasted, user-overridable baselines); GnuCash's budgeted-vs-actual side-by-side report layout.

### 1.4 Out of scope (v1)

Multi-user/RBAC, real-time bank aggregation, double-entry general ledger enforcement, multi-currency consolidation with FX translation (single workspace currency in v1; schema reserves the hooks), hierarchical forecast reconciliation, balance-sheet/cash-flow statements at full rigor (P&L-first; BS modeled as point-in-time balances only where needed).

---

## 2. The Four Budgeting Methods

### 2.1 Final decision

Implement the **CFI canonical four derivation engines** — this taxonomy is verified (CFI lists exactly these four; Peak Frameworks corroborates verbatim):

```
BudgetMethod = { INCREMENTAL, ACTIVITY_BASED, VALUE_PROPOSITION, ZERO_BASED }
```

**Static / Flexible / Rolling are NOT competing methods.** They are orthogonal modifiers that wrap any of the four:

```
volumeMode = { STATIC, FLEXIBLE }          # how the budget responds to actual volume
cadence    = { PERIODIC, ROLLING(horizon) } # how/when the budget re-extends in time
```

This yields expressive combinations like "Rolling ABB" or "Flexible Incremental."

> **Verdict-driven correction:** The research framed a parallel "List B" of exactly four control methods. That was an oversimplification — AccountingTools actually lists six models (including ZBB and Incremental among them) and Lumen lists three. We therefore **do not** present Static/Flexible/Rolling as a rival canon; we adopt only the *orthogonality insight*, which is sound. The four derivation engines are the product's "budgeting methods."

### 2.2 Shared input layer (all four engines read this)

- **Actuals store** — historical spend/revenue by `period × cost_center × account` (the `entries` table, `scenario='ACTUAL'`).
- **Drivers store** — operational/forecast drivers: volumes, headcount, sales target, inflation %, growth %, FX, activity counts.

Engines differ only in *how* they transform this data:

| Engine | Uses actuals as… | Uses drivers as… |
|---|---|---|
| Incremental | mechanical baseline | uplift % |
| ABB | source of driver **rates** (cost pool ÷ units) | future **volumes** |
| Value-Proposition | evidence for cost/value scoring | projected value/ROI inputs |
| ZBB | evidence to size & justify each package | benefit quantification |

### 2.3 Method 1 — Incremental Budgeting

**Definition (verified, CFI "Types of Budgets"):** take last year's figures and add/subtract a percentage.

> **Verdict-driven corrections:**
> 1. CFI is *internally inconsistent* on the baseline — the types page says "last year's **actual** figures," the dedicated incremental page says "marginal changes to the current **budget**" and explicitly states **"there is no standard formula."** **Product decision: use prior ACTUALS as the baseline, documented as a deliberate choice.**
> 2. The formula below is **our own engineering formalization**, not a CFI-stated formula. It is implementable and reasonable, but it is a design choice, not canon.

**Inputs:** prior-period actuals `A_i` per line; adjustment factor `g_i` (inflation % + growth % + strategic %), or flat global %; optional one-off adjustments.

**Algorithm:**
1. Load prior actuals `A_i` per line.
2. Resolve `g_i = inflation% + growth% + strategic%` (the additive decomposition is a design choice).
3. `Budget_i = A_i × (1 + g_i) + Adjustment_i`.
4. Sum to totals; optional cap/floor; emit for approval.
5. After actuals arrive: variance feeds next baseline.

**Formula (product-defined):** `Budget_i = PriorActual_i × (1 + g_i) + Adjustment_i`

**Unit-test fixture (synthetic — not source-attributed):** `200,000 × 1.08 + 15,000 = 231,000`. If actual = 225,000, variance = `225,000 − 231,000 = −6,000` → **favorable** for an expense line (under budget); next baseline = 225,000.

### 2.4 Method 2 — Activity-Based Budgeting (ABB)

**Definition (verified, CFI verbatim):** "determines the amount of inputs required to support the targets or outputs set by the company." **Formula verified against Wall Street Mojo** — this engine's algorithm is genuinely source-grounded.

**Inputs:** output/sales target; activities required; cost driver per activity; forecast driver volume per activity; driver rate from prior cost pool ÷ prior driver units.

**Algorithm:**
1. Set output target.
2. Enumerate activities `a`.
3. For each, forecast volume `V_a = output × driver-per-output`.
4. Driver rate `R_a = prior_cost_pool_a / prior_driver_units_a`.
5. `Budget_a = V_a × R_a`.
6. Sum activities; add non-activity (fixed) costs.

**Formulas:** `R_a = CostPool_a / DriverUnits_a` ; `Budget_a = V_a × R_a` ; `Total = Σ(V_a × R_a) + FixedCosts`

**Unit-test fixture (synthetic, arithmetic verified):** setup `R = 400,000/700 = 571.43`, `800 × 571.43 = 457,144`; inspection `R = 280,000/15,500 = 18.06`, `16,000 × 18.06 = 288,960`; total `746,104`.

### 2.5 Method 3 — Value-Proposition (Priority-Based) Budgeting

**Definition (verified):** ensure every expense delivers value; CFI's three test questions confirmed verbatim ("Why is this amount included?", "Does it create value?", "Does value outweigh cost?"). Alias "Priority-Based Budgeting" confirmed (Datarails).

> **Verdict-driven correction:** Datarails defines this as a **qualitative mindset with NO algorithm or formula.** The greedy/knapsack optimizer below is **our own engineering construction** to make the method autonomously executable — it must be labeled as a product design choice, not source canon. Critically, the value scores are **subjective user inputs the optimizer cannot manufacture**; provide a guided scoring rubric/wizard.

**Inputs:** candidate initiatives, each with cost `C_j`, value score `Val_j` (from a configurable rubric), and a total budget cap.

**Algorithm (product-defined optimizer):**
1. Compute `ROI_j = Val_j / C_j`.
2. Sort descending by `ROI_j`.
3. Greedily fund while cumulative cost ≤ cap (offer optional 0/1 knapsack solver for optimal mix under a hard cap).
4. Items below cutline deferred.
5. Output funded set + slack.

**Formula (product-defined):** greedy by descending `Val_j / C_j` under cap; optional knapsack `max Σ Val_j s.t. Σ C_j ≤ Cap`.

**Unit-test fixture (synthetic, verified):** cap 100,000; A(40k,90→2.25), B(30k,75→2.50), D(20k,50→2.50), C(50k,60→1.20). Fund B+D+A = 90,000 (value 215), defer C, slack 10,000.

### 2.6 Method 4 — Zero-Based Budgeting (ZBB)

**Definition (verified, Wikipedia verbatim):** "requires all expenses to be justified and approved in each new budget period." Origin verified: Pyhrr at Texas Instruments, HBR 1970; Georgia FY1973; US federal 1976 Act / 1977 implementation. **The rank-and-fund algorithm IS genuinely source-derived** (Wikipedia, AccountingTools, eFinanceManagement).

**Inputs:** decision units (independently analyzable departments/programs); decision packages per unit (objective, cost, benefit, alternatives, service levels min/current/enhanced); ranking criterion; total funds.

**Algorithm:**
1. Define decision units.
2. Generate decision packages at incremental service levels, each with cost + benefit.
3. Rank ALL packages org-wide by `Benefit/Cost` (or net `Benefit − Cost`).
4. Fund top-down until funding envelope exhausted; below cutoff = unfunded.
5. Approved set IS the budget — built from zero.

**Formula:** for each package `p`: `N_p = Benefit_p − Cost_p` (or ratio `Benefit_p/Cost_p`); rank descending; fund while `Σ Cost_p ≤ TotalFunds`.

**Unit-test fixture (synthetic, verified):** funds 250,000; P1(120k,100→0.83), P2(60k,70→1.17), P3(90k,40→0.44), P4(80k,25→0.31). Order P2,P1,P3,P4 → fund P2+P1 = 180,000; remaining 70,000 competes for P3/P4.

**Practicality note:** offer a "ZBB-lite" mode — re-justify only discretionary/flagged categories above a configurable threshold — since full-rigor ZBB is labor-intensive.

### 2.7 Orthogonal modifiers

- **Flexible mode** (verified formula): `FlexAllowance = (StdVariableCostPerUnit × ActualVolume) + BudgetedFixedCost`. Re-evaluates variable lines at actual volume; fixed lines unchanged.
- **Rolling mode:** a scheduler. At period close, horizon = `[t+1 … t+N]`; drop oldest, append new, re-run the chosen engine, keep `N` constant.

### 2.8 Feedback loop

After each cycle, run variance analysis and feed results back: as next baseline (Incremental), refreshed driver rates (ABB), and realized-ROI evidence (Value-Proposition/ZBB scoring).

---

## 3. Forecasting Engine Design

### 3.1 Two-tier model menu

**Tier 1 — Explainable classic FP&A** (finance teams trust/audit these; expose for manual selection):

| Method | Formula | Notes |
|---|---|---|
| Straight-line / growth-rate | `g = (V_t − V_{t-1})/V_{t-1}`; `F_{t+1} = V_t × (1+g)` | Stable mature lines; ignores seasonality |
| Moving average | `MA_t = (1/n)Σ y_{t-i}`; `F_{t+1} = MA_t` | Lags turning points; no trend extrapolation |
| Simple linear regression | `Y = mX + c` (OLS) | One driver/time |
| Multiple linear regression | `Y = b0 + b1X1 + … + bkXk` (OLS) | Drivers must themselves be forecast; watch multicollinearity |

**Tier 2 — Autonomous statistical** (engine auto-selects):

| Model | Captures | Library API |
|---|---|---|
| ARIMA/SARIMA `(p,d,q)(P,D,Q)_s` | autocorrelation, trend (d), seasonality (seasonal order); SARIMAX adds exog drivers = "regression with SARIMA errors" | statsforecast `AutoARIMA`; statsmodels `SARIMAX`; pmdarima `auto_arima` (fallback) |
| ETS / Holt-Winters | level/trend/seasonality; ETS(E,T,S) state-space | statsforecast `AutoETS`; statsmodels `ETSModel` |
| Theta / CES | trend + decomposition | statsforecast `AutoTheta`, `AutoCES` |
| Prophet | piecewise trend + multi-seasonality + holidays; robust to gaps | `prophet.Prophet` (optional, for messy business calendars) |
| Naive / SeasonalNaive / Drift / WindowAverage | baselines + MASE denominators | statsforecast |

> **Verdict note on intervals:** classic `statsmodels.holtwinters.ExponentialSmoothing` gives point forecasts but **no analytic intervals** — use `ETSModel` (state-space) or conformal intervals when intervals are required. Prophet's default `yhat_lower/upper` (MAP, `mcmc_samples=0`) capture trend uncertainty + observation noise but **not full parameter uncertainty**, so they can be optimistic — prefer conformal and validate coverage.

### 3.2 Autonomous auto-selection pipeline

Per series:

1. **Clean & regularize** — resample to fixed frequency; fill/flag gaps.
2. **Detect frequency & seasonal period `m`** — set `m` a priori by calendar (12 monthly, 4 quarterly, 7 daily-weekly, 52 weekly) and let auto-models confirm seasonal differencing (OCSB default / Canova-Hansen for ARIMA) or seasonal component (AICc for ETS). Optional ACF-peak / periodogram detector for non-calendar periods; STL strength-of-seasonality `Fs = max(0, 1 − Var(R_t)/Var(S_t+R_t))` as a gate.
3. **Build candidate pool** sized to data — `SeasonalNaive, Naive, WindowAverage, AutoETS, AutoARIMA, AutoTheta, AutoCES`, optionally Prophet.
4. **Rolling-origin cross-validation** (NOT random k-fold — that leaks future into past):
   `sf.cross_validation(df, h=<business horizon>, step_size, n_windows>=3)` → columns `[unique_id, ds, cutoff, y, <model>]`. Train only on data before each cutoff; roll forward; average per-window error.
5. **Score with MASE** (primary), RMSE/MAE as tie-breaker. MAPE shown in UI only for comfortably positive series; **sMAPE not used for ranking** (Hyndman & Koehler advise against; fix one sMAPE definition if ever displayed).
6. **Select lowest-MASE model** per series (outer selector across families; AICc is the inner selector within `AutoARIMA`/`AutoETS`).
7. **Refit winner on full history**; forecast `h` with prediction intervals.

**Inner vs outer:** `AutoARIMA`/`AutoETS` minimize AICc internally; CV minimizes MASE across families.

### 3.3 Error metric formulas (verified)

```
e_t = y_t − ŷ_t
MAE   = mean(|e_t|)
RMSE  = sqrt(mean(e_t²))
MAPE  = 100 × mean(|e_t / y_t|)          # undefined/explosive near y_t=0; penalizes over-forecasts more
sMAPE = mean(200·|y_t−ŷ_t| / (|y_t|+|ŷ_t|))   # display only, never for ranking
MASE  = mean(|e_t|) / Q
  Q_nonseasonal = (1/(T−1)) Σ_{t=2..T} |y_t − y_{t-1}|
  Q_seasonal    = (1/(T−m)) Σ_{t=m+1..T} |y_t − y_{t-m}|
```
MASE is scale-invariant, defined for zero/intermittent data; `MASE < 1` beats naive. **Primary selection metric.**

### 3.4 Short-series fallback

> **Verdict-driven correction:** the "≥2 full seasonal cycles (≥24 monthly points)" gate is a **pragmatic product heuristic, NOT Hyndman-endorsed theory** — Hyndman explicitly rejects fixed minimum-observation thresholds as "misleading and unsubstantiated" and asserts only the theoretical floor of "more observations than parameters." Implement the 2-cycle gate as a heuristic **and** lean on the auto-models' own AICc/seasonal-difference tests and STL `Fs`.

Gate: allow seasonal models (SARIMA/Holt-Winters/seasonal ETS) only when `n ≥ 2m`; below that fall back through **Holt → SES → Seasonal Naive → Naive**. Naive baselines (verified):
```
Naive:          ŷ_{t+h} = y_t
Seasonal Naive: ŷ_{t+h} = y_{t+h−m(k+1)}
Drift:          ŷ_{t+h} = y_t + h·(y_t − y_1)/(t−1)
```
Industry thresholds (Microsoft Dynamics) switch to naive below 14d/12w/12m with no detected seasonality. These naive errors double as the MASE denominator.

### 3.5 Prediction intervals

- **Default: distribution-free conformal**, calibrated on CV residuals — `sf.forecast(h, level=[80,90,95])` emits nested `<model>-lo-XX / <model>-hi-XX` columns (80% ⊂ 90% ⊂ 95%). Validate empirical coverage against nominal on CV windows.
- **Parametric fallback:** `SARIMAX.get_forecast(h).conf_int(alpha)`; `ETSModel.get_prediction().summary_frame()`; Prophet `interval_width`.
- Always surface lower/upper bands at 80% and 95% alongside the point forecast.

**Constraint to enforce:** conformal calibration requires `n_windows × h < series_length` — interacts with the short-series gate.

### 3.6 Operational notes

- Cache per series: winning model family, hyperparameters, CV error, chosen `m`. Re-run full model selection monthly; re-fit cached winner more frequently for low latency. Log the CV scoreboard for FP&A auditability.
- Driver-based forecasts require the drivers themselves to be forecast/supplied — support scenario inputs (`SARIMAX` with exog or multiple regression).
- Weekly data has non-integer `m ≈ 52.18`; multi-seasonal daily series (weekly+yearly) may need MSTL/Fourier rather than a single integer `m`.

---

## 4. Variance Analysis

All 12 core formulas below are **verified** against Saylor/Lumen/AccountingTools (Jerry's Ice Cream worked examples reconcile exactly). No formula was refuted.

### 4.1 Master hierarchy (verified)

```
Static (master) Budget Variance = Flexible Budget Variance + Sales Volume Variance
```
- **Flexible budget** restates plan at ACTUAL output: variable lines = `BudgetedRate × ActualUnits`; fixed costs unchanged.
- `FlexibleBudgetVariance = Actual − Flexible`  (isolates price/rate/efficiency/spending)
- `SalesVolumeVariance = Flexible − Static`  (isolates pure quantity effect)
- Assert `Static = Flexible + SalesVolume` as an automated reconciliation unit test.

### 4.2 Sign convention — the single most error-prone area (verified)

Compute every variance left-to-right as **`Actual − Standard/Budget`**.

- For **COST** accounts: positive = **UNFAVORABLE**, negative = **FAVORABLE** (Saylor: "all positive variances are unfavorable, all negative are favorable" — holds *only* for costs).
- For **REVENUE / CM / profit**: polarity **inverts** — positive = **FAVORABLE**.

**Product rule:** persist the **signed numeric variance** plus a boolean `is_favorable` **derived from `account_type`, never from sign alone**:
```
is_favorable = (account is cost) ? (variance < 0) : (variance > 0)
```
**Favorable-normalized variance** (so "positive = good" everywhere): `favorable_variance = variance × sign_factor` where `sign_factor = +1` for revenue/income, `−1` for cost/COGS/opex. (Verified correct.)
Doc caveat: "favorable" ≠ "good" — cheap low-grade material gives a favorable price variance but an unfavorable usage variance (interrelated).

### 4.3 Budget-vs-Actual (verified, with nuance)

```
Absolute variance = Actual − Budget
% variance = (Actual − Budget) / |Budget| × 100      # undefined when Budget=0 → N/A
```
Use `|Budget|` to keep sign meaningful for negative bases; **rely on the favorable/unfavorable flag (account-type-derived), not the raw % sign**, for interpretation.

> **Verdict nuance:** the "|%| > 5–10% AND |$| > floor" dual materiality test is a **practitioner heuristic, not a mandated standard.** Make thresholds **configurable per account category**; consider statistical control-limit thresholds as an alternative. Guard divide-by-zero with `NULLIF`.

### 4.4 Cost variances (verified — `SQ`/`SH` flex to ACTUAL output)

```
Material Price    = (AP − SP) × AQ purchased       # e.g. (1.20−1.00)×440,000 = +88,000 Unfav
Material Quantity = (AQ used − SQ) × SP            # SQ = std/unit × ACTUAL units; (399,000−420,000)×1.00 = −21,000 Fav
Labor Rate        = (AR − SR) × AH                 # (15−13)×18,900 = +37,800 Unfav
Labor Efficiency  = (AH − SH) × SR                 # SH = std/unit × ACTUAL units; (18,900−21,000)×13 = −27,300 Fav
VOH Spending      = (AR − SR) × AH = ActualVOH − (AH × SR)
VOH Efficiency    = (AH − SH) × SR
Fixed OH Spending = Actual FOH − Budgeted FOH      # 136,000−140,280 = −4,280 Fav; NO efficiency variance for fixed OH
```

**Fixed OH Volume Variance — direction corrected and verified:**
```
Fixed OH Volume = Budgeted FOH − Applied FOH = StdFOHrate/unit × (Budgeted units − Actual units)
                # 140,280 − 147,000 = −6,720 Fav; equivalently 0.70 × (200,400 − 210,000) = −6,720 Fav
```
> **Verdict-driven correction:** the formula is definitively **`Budgeted − Applied`** (NOT `Applied − Budgeted`). Over-production (actual > denominator) ⇒ over-absorbed ⇒ **Favorable**. This is a pure absorption-costing capacity artifact with **no cash/spending meaning** — **label it as such in the UI, exclude it from spend-control dashboards, and note it does not arise under pure variable/contribution costing.**

Material price recognition (purchase vs usage) is an **accounting-policy toggle**; default to **purchase** (AQ purchased) but allow usage so price+usage reconcile cleanly when purchases = usage.

### 4.5 Sales variances (verified)

```
Sales Price  = (Actual Price − Budgeted Price) × Actual Units Sold   # uses ACTUAL units; (10.50−10.00)×4,835,000 = +2,417,500 Fav
Sales Volume = (Actual Units − Budgeted Units) × Budgeted CM/unit    # (4,835,000−5,000,000)×1.15 = −189,750 Unfav
```
**Multiplier basis is configurable** — default **contribution margin per unit** (ties to operating-income bridge); allow profit/unit (absorption) and price/unit (revenue-only). Document the chosen basis on every report.

**Multiproduct split — use the Horngren formula, NOT the AccountingTools one:**

> **Verdict-driven correction (highest priority):** AccountingTools defines "sales mix variance" as `(Actual units − Budgeted units) × budgeted CM` — that is actually the per-product **sales volume** variance and does **NOT** isolate mix. The build **MUST** use the accounting-simplified/Horngren formulation (pivot on actual-total-at-budgeted-mix) so Mix + Quantity reconcile to Volume.

```
Sales Mix (per product)      = (Actual units − ActualTotalUnits × Budgeted mix%) × Budgeted CM/unit
Sales Quantity (per product) = (ActualTotalUnits − BudgetedTotalUnits) × Budgeted mix% × Budgeted CM/unit
Sales Mix + Sales Quantity = Sales Volume Variance
```
**Verified reconciliation (Aliengear):** Mix `−700,000 + 175,000 = −525,000`; Quantity `+400,000 + 150,000 = +550,000`; `−525,000 + 550,000 = +25,000` = Sales Volume. Mix only meaningful within substitutable product families; handle new/discontinued products (no baseline) explicitly.

### 4.6 Presentation

- **Headline: variance bridge / waterfall** — Budget → Volume → Mix → Price → cost drivers → Actual, with bars that **provably sum** to the total change. For multi-period PVM, **average the decomposition across calculation orders** (PVM vs VPM differ) so components reconcile exactly and mix is not double-counted in volume; document the price×volume interaction convention.
- Side-by-side **Budget | Actual | $ Var | % Var | F/U flag** table (GnuCash-style layout, hledger-style "% consumed").
- **Drill-down** by entity, product/SKU, cost center, account, period — variances stored at finest grain, rolled up via dimension hierarchies, each row tagged with a driver/owner.
- Forecast variance (Actual − Forecast) supported identically.

---

## 5. Data Model

### 5.1 Architectural decisions

- **DB layout = LONG/tidy.** One fact row per `account × period × dimension-combo × scenario × version`, single `amount` column, `period_key` key. Adding a period = INSERTs, not DDL. Trivial GROUP BY / variance joins / indexing.
- **Upload template = WIDE.** Accounts down rows, periods (`YYYY-MM`) across columns — how finance teams build budgets in Excel. Importer pivots wide→long. A parallel LONG CSV template serves ERP/system feeds.
- **Money = INTEGER minor units (cents).** Never float (IEEE-754 can't represent most decimals exactly; SQLite has no decimal type). `amount_minor INTEGER`, `currency` ISO 4217, `minor_unit_scale` (default 2). Display = `amount_minor / 10^scale`. REAL only for derived `variance_pct`.
- **Time = MONTHLY grain**, smart `period_key INTEGER = YYYYMM`. Precompute fiscal attributes from a configurable `fiscal_year_start_month`. Roll up via GROUP BY.
- **Scenario = explicit dimension** (`ACTUAL/BUDGET/FORECAST`); budgets carry `budget_version_id`, forecasts carry `forecast_run_id`; actuals carry neither.
- **Sentinel `id=0` ("Unallocated/All")** in every dimension so all fact FKs are NOT NULL.
- **Sign:** users type positive magnitudes; store `normal_balance` + `sign_factor` on accounts; `Net Income = SUM(amount_minor × sign_factor)`.

### 5.2 Chart of accounts (numbering / normal balance)

```
account_type ∈ {REVENUE, COGS, OPEX, OTHER_INCOME, OTHER_EXPENSE, ASSET, LIABILITY, EQUITY}
Numbering: Assets 1000–1999, Liabilities 2000–2999, Equity 3000–3999,
           Revenue 4000–4999, COGS 5000–5999, OpEx 6000–6999, Other/Tax 7000–7999
Normal balance: ASSET/EXPENSE/COGS/OPEX/OTHER_EXPENSE = DEBIT; LIABILITY/EQUITY/REVENUE/OTHER_INCOME = CREDIT
sign_factor (P&L): REVENUE/OTHER_INCOME = +1; COGS/OPEX/OTHER_EXPENSE = −1
```
Hierarchy via `parent_account_id`; only `is_postable=1` leaves accept entries; roll-up nodes computed.

### 5.3 Final SQLite tables (key columns)

```sql
-- accounts
CREATE TABLE accounts (
  account_id INTEGER PRIMARY KEY, account_code TEXT UNIQUE NOT NULL, account_name TEXT NOT NULL,
  account_type TEXT NOT NULL CHECK(account_type IN
    ('REVENUE','COGS','OPEX','OTHER_INCOME','OTHER_EXPENSE','ASSET','LIABILITY','EQUITY')),
  statement_section TEXT NOT NULL CHECK(statement_section IN('PL','BS')),
  account_category TEXT, parent_account_id INTEGER REFERENCES accounts(account_id),
  normal_balance TEXT NOT NULL CHECK(normal_balance IN('DEBIT','CREDIT')),
  sign_factor INTEGER NOT NULL CHECK(sign_factor IN(-1,1)),
  balance_type TEXT NOT NULL DEFAULT 'FLOW' CHECK(balance_type IN('FLOW','BALANCE')),  -- BS = point-in-time
  is_postable INTEGER NOT NULL DEFAULT 1, sort_order INTEGER, is_active INTEGER NOT NULL DEFAULT 1);

-- conformed dimensions (one each; dim_entity adds currency TEXT)
CREATE TABLE dim_department (department_id INTEGER PRIMARY KEY, department_code TEXT UNIQUE NOT NULL,
  department_name TEXT NOT NULL, parent_department_id INTEGER REFERENCES dim_department(department_id),
  is_active INTEGER NOT NULL DEFAULT 1);
-- repeat as dim_entity(entity_id,...,currency TEXT), dim_project(project_id,...), dim_region(region_id,...)

-- periods (month grain, smart key)
CREATE TABLE periods (period_key INTEGER PRIMARY KEY, year INTEGER NOT NULL,
  month_num INTEGER NOT NULL CHECK(month_num BETWEEN 1 AND 12), month_name TEXT, quarter INTEGER,
  period_start_date TEXT NOT NULL, period_end_date TEXT NOT NULL,
  fiscal_year INTEGER NOT NULL, fiscal_quarter INTEGER NOT NULL, fiscal_period_num INTEGER NOT NULL,
  is_closed INTEGER NOT NULL DEFAULT 0);

CREATE TABLE budget_versions (budget_version_id INTEGER PRIMARY KEY, version_name TEXT NOT NULL,
  fiscal_year INTEGER NOT NULL, method TEXT, volume_mode TEXT, cadence TEXT,
  status TEXT NOT NULL DEFAULT 'DRAFT' CHECK(status IN('DRAFT','SUBMITTED','APPROVED','ARCHIVED')),
  is_active INTEGER NOT NULL DEFAULT 0, created_by TEXT, created_at TEXT NOT NULL,
  UNIQUE(version_name, fiscal_year));

CREATE TABLE forecast_runs (forecast_run_id INTEGER PRIMARY KEY, run_label TEXT NOT NULL,
  as_of_period_key INTEGER REFERENCES periods(period_key), method TEXT, selected_model TEXT,
  cv_mase REAL, assumptions_json TEXT, created_by TEXT, created_at TEXT NOT NULL,
  UNIQUE(run_label, as_of_period_key));

-- entries (the long fact table: actual/budget/forecast)
CREATE TABLE entries (entry_id INTEGER PRIMARY KEY,
  account_id INTEGER NOT NULL REFERENCES accounts(account_id),
  period_key INTEGER NOT NULL REFERENCES periods(period_key),
  entity_id INTEGER NOT NULL REFERENCES dim_entity(entity_id),
  department_id INTEGER NOT NULL REFERENCES dim_department(department_id),
  project_id INTEGER NOT NULL REFERENCES dim_project(project_id),
  region_id INTEGER NOT NULL REFERENCES dim_region(region_id),
  scenario TEXT NOT NULL CHECK(scenario IN('ACTUAL','BUDGET','FORECAST')),
  budget_version_id INTEGER REFERENCES budget_versions(budget_version_id),
  forecast_run_id INTEGER REFERENCES forecast_runs(forecast_run_id),
  amount_minor INTEGER NOT NULL, currency TEXT NOT NULL DEFAULT 'USD',
  minor_unit_scale INTEGER NOT NULL DEFAULT 2, source TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  CHECK((scenario='BUDGET'   AND budget_version_id IS NOT NULL AND forecast_run_id IS NULL) OR
        (scenario='FORECAST' AND forecast_run_id   IS NOT NULL AND budget_version_id IS NULL) OR
        (scenario='ACTUAL'   AND budget_version_id IS NULL     AND forecast_run_id IS NULL)));
CREATE UNIQUE INDEX ux_entries_natural ON entries(
  account_id,period_key,entity_id,department_id,project_id,region_id,scenario,
  IFNULL(budget_version_id,0),IFNULL(forecast_run_id,0));
CREATE INDEX ix_entries_period ON entries(period_key);
CREATE INDEX ix_entries_acct   ON entries(account_id,scenario);

-- variance_results (derived/materialized)
CREATE TABLE variance_results (variance_id INTEGER PRIMARY KEY,
  account_id INTEGER NOT NULL, period_key INTEGER NOT NULL,
  entity_id INTEGER NOT NULL, department_id INTEGER NOT NULL, project_id INTEGER NOT NULL, region_id INTEGER NOT NULL,
  base_scenario TEXT NOT NULL, compare_scenario TEXT NOT NULL,
  budget_version_id INTEGER, forecast_run_id INTEGER,
  variance_kind TEXT,           -- BUDGET_VS_ACTUAL | FLEX_BUDGET | SALES_VOLUME | SALES_PRICE | SALES_MIX | SALES_QTY | MAT_PRICE | ... 
  actual_minor INTEGER, comparison_minor INTEGER, variance_minor INTEGER,
  favorable_variance_minor INTEGER, variance_pct REAL,
  variance_status TEXT CHECK(variance_status IN('FAVORABLE','UNFAVORABLE','NEUTRAL')),
  is_material INTEGER, computed_at TEXT NOT NULL);
```
Plus a `change_log` table (who/when/old→new) for manual-grid edits and optimistic concurrency via `updated_at`.

### 5.4 CSV/Excel upload template column spec

**WIDE (default, Excel/CSV) columns:**
`account_code` (req, must exist + `is_postable`), `account_name` (optional, informational), `entity_code` (req), `department_code` (req, `UNALLOC` if none), `project_code` (opt, default `NONE`), `region_code` (opt, default `ALL`), `currency` (opt ISO 4217, default workspace), then one numeric column per period named `YYYY-MM` (e.g. `2026-01 … 2026-12`).

Numeric cells: plain numbers — **no** currency symbols, **no** thousands separators, `.` decimal only; **blank = NULL (not 0)**; negatives allowed for contra/credit.

**Budget/Forecast** reuse the same shape + validations plus version metadata: budget requires `budget_version` (header or column); forecast requires run label + as-of date + method. Re-upload UPSERTs only that version/run.

**LONG variant:** `account_code, entity_code, department_code, project_code, region_code, period (YYYY-MM), amount, currency`.

**Validation rules (fail fast, per-row error report):**
- Required fields present; `account_code` resolves to an existing **postable** account (reject roll-up nodes).
- Dimension codes resolve to active members (default reject unknowns with clear error; auto-create optional).
- Dates ISO 8601 `YYYY-MM` (or `YYYY-MM-DD` coerced to month); reject ambiguous locale dates.
- Numeric parse: reject values with symbols/`%`/thousands separators; require `.` decimal; enforce numeric type (CSV is typeless).
- Reject in-file duplicate natural keys; UPSERT against `ux_entries_natural` (replace by default — configurable replace vs sum per upload).
- Reject/warn writes to `is_closed=1` (locked) periods.
- Optional sign warnings (negative expense / negative revenue).

### 5.5 Manual entry grid

2-D grid: rows = postable accounts (grouped with computed subtotals), columns = target FY months + read-only Total. User fixes context (entity/department/project/region/scenario/version) → each editable cell maps to exactly one long `entries` row via the natural key. Clearing a cell deletes the row. Subtotals computed, never stored. "Copy-from" seeds a budget grid from prior-year actuals × growth, or clones a forecast run.

---

## 6. Recommended Open-Source Tech Stack

All choices below are **license-audited as of 2026-06-18** (PyPI JSON / npm registry / GitHub LICENSE) and are OSI-permissive.

### 6.1 Backend

| Library | License | Version | Role |
|---|---|---|---|
| FastAPI | MIT | 0.137.x | Web framework |
| Pydantic v2 | MIT | 2.13.x | Validation/serialization |
| SQLAlchemy 2.x | MIT | 2.0.x | ORM/core |
| SQLModel | MIT | 0.0.x | Thin model layer (drop to raw SQLAlchemy for complex analytical queries) |
| Alembic | MIT | 1.18.x | Migrations |
| Uvicorn | BSD-3 | 0.49.x | ASGI server |
| python-multipart | Apache-2.0 | 0.0.32 | File/form uploads |
| aiosqlite | MIT | 0.22.x | Only if async DB needed |

**SQLite:** enable WAL mode. Synchronous SQLAlchemy is the default — single-user local; only adopt aiosqlite if long forecast jobs justify async (prefer a background task instead).

### 6.2 Data & Excel

| Library | License | Role |
|---|---|---|
| pandas | BSD-3 | Primary dataframe |
| polars | MIT | Optional, fast large imports |
| python-calamine | MIT | Excel **read** (`engine='calamine'`, ~5× faster) |
| openpyxl | MIT | Excel **write** (.xlsx) |

**Parse all spreadsheets server-side in Python** — sidesteps the SheetJS npm/CVE problem entirely.

### 6.3 Forecasting

| Library | License | Role |
|---|---|---|
| **Nixtla statsforecast** | **Apache-2.0** | **Autonomous core** — AutoARIMA/AutoETS/AutoTheta/AutoCES + SeasonalNaive/Naive in one call, built-in `cross_validation`, conformal intervals |
| statsmodels | BSD-3 | Transparent single fits, SARIMAX-with-exog, ETSModel analytic intervals |
| scikit-learn | BSD-3 | Regression utilities |
| numpy / scipy | BSD-3 | Numerical foundation |
| Prophet | MIT | Optional — series with strong holiday/calendar effects (post-1.1 backend is BSD-3 Stan/cmdstanpy; **no GPL**) |
| pmdarima | MIT | Optional drop-in `auto_arima` fallback only |
| sktime | BSD-3 | Optional unified API |

> numpy/scipy bundle GCC runtime (GPL-with-GCC-exception) and libquadmath (LGPL) as compiled runtime deps; the GCC Runtime Library Exception and LGPL dynamic linking impose **no copyleft** on our code. Both projects' own license is BSD-3.

### 6.4 Frontend

| Library | License | Role |
|---|---|---|
| React 19 + Vite + TypeScript | MIT | SPA base |
| Recharts 3.x | MIT | Default charts (waterfall, line+interval bands) |
| Apache ECharts | Apache-2.0 | Upgrade path for large-dataset/canvas perf |
| TanStack Table v8 | MIT | Data grid (avoids AG Grid Enterprise landmine) |
| shadcn/ui + Tailwind v4 | MIT | UI components |
| TanStack Query v5 | MIT | Server state |
| react-hook-form + zod | MIT | Forms; share zod schemas across form + API validation |

### 6.5 Tooling

ruff (MIT), mypy (MIT), pytest (MIT), pytest-playwright (Apache-2.0); ESLint (MIT), Prettier (MIT), Vitest (MIT), Playwright (Apache-2.0).

### 6.6 Rejected / guardrail libraries

| Rejected | Reason |
|---|---|
| **ag-grid-enterprise** | npm license literally `Commercial` (~USD 999/dev EULA). Use `ag-grid-community` (MIT) or TanStack Table. Enterprise silently gates pivot/aggregation/range-selection/server-side-row-model/Excel-export. |
| **@mui/x-data-grid-pro / -premium** | Commercial (`SEE LICENSE IN LICENSE`). If using MUI, restrict to the MIT `@mui/x-data-grid` community tier. |
| **SheetJS Pro** + npm `xlsx` | CE is Apache-2.0, but npm is frozen at vulnerable **0.18.5** (CVE-2023-30533 prototype pollution + ReDoS); current 0.20.x is **CDN-only**. Pro is commercial. **Decision: parse server-side; do not use browser SheetJS.** If ever unavoidable, install CE 0.20.x from cdn.sheetjs.com, never npm. |
| **Dash Enterprise** | Commercial hosting platform. (plotly.js / plotly Python / OSS Dash are all MIT — but we use React, so Dash is unneeded.) |
| **Highcharts, FullCalendar scheduler plugins** | Not in scope; Highcharts is non-OSI for commercial use; FullCalendar premium scheduler plugins are commercial. If a calendar is ever added, use only MIT `@fullcalendar/*` core. |
| Prior-art apps (Firefly III, Maybe/Sure, Lago, OpenBB AGPL; GnuCash GPLv2+; hledger GPLv3) | These are **comparable products, not dependencies** — fine to learn from, but **never incorporate their code** (copyleft). |

**CI license gate (mandatory):** `pip-licenses` (Python) + `license-checker` (npm) that **fails the build** on any GPL/AGPL/SSPL/BSL/`Commercial`/`SEE LICENSE IN LICENSE` dependency. Pin versions so a transitive bump cannot silently pull in `ag-grid-enterprise` or an `@mui/x-*-pro` package. Maintain a NOTICE/attributions file.

---

## 7. System Architecture

### 7.1 Backend module breakdown

```
app/
  api/            # FastAPI routers (thin; validation via Pydantic/zod-mirrored schemas)
  domain/
    coa/          # chart of accounts, dimensions, periods
    ingestion/    # upload parse (calamine/openpyxl) -> validate -> pivot wide->long -> UPSERT
    budgeting/    # 4 engines + modifiers
      incremental.py  activity_based.py  value_proposition.py  zero_based.py
      modifiers.py    # flexible-budget allowance, rolling scheduler
    forecasting/
      classic.py      # straight-line, MA, OLS simple/multiple
      auto_select.py  # candidate pool -> rolling-origin CV -> MASE rank -> refit winner
      seasonality.py  # m a priori + ACF/periodogram + STL Fs gate
      intervals.py    # conformal (default) + parametric fallback
      cache.py        # per-series winning model/hyperparams/CV score
    variance/
      flexible_budget.py  cost_variances.py  sales_variances.py  # incl. Horngren mix/qty
      sign.py             # account-type-derived favorable/unfavorable
      materiality.py      # configurable dual thresholds
      bridge.py           # order-averaged PVM waterfall data
  db/             # SQLAlchemy models, Alembic migrations, session (WAL)
  services/       # orchestration across domains
```

### 7.2 API surface sketch

```
# Reference data
GET    /api/accounts            POST /api/accounts            (CRUD; dimensions analogous)
GET    /api/periods

# Ingestion
POST   /api/uploads            (multipart; ?scenario=&budget_version=&forecast_run=) -> per-row validation report
GET    /api/templates/{scenario}.xlsx   (pre-seeded with active COA + target-year periods)

# Entries / manual grid
GET    /api/entries            (filter by scenario/version/dims/period range; returns long, UI pivots wide)
PUT    /api/entries/cell       (upsert one cell -> one long row)

# Budgeting
POST   /api/budgets/run        ({method, volume_mode, cadence, version_name, drivers, cap?, packages?}) -> budget_version_id
GET    /api/budgets/{version_id}

# Forecasting
POST   /api/forecasts/run      ({series_selector, horizon, level:[80,95], allow_seasonal, model_override?}) -> forecast_run_id + CV scoreboard
GET    /api/forecasts/{run_id} (point + lo/hi bands + selected model + MASE)

# Variance
POST   /api/variance/compute   ({base:'ACTUAL', compare:'BUDGET', version_id|run_id, grain, kinds:[...]}) 
GET    /api/variance           (table)
GET    /api/variance/bridge    (order-averaged waterfall data)
```

### 7.3 Frontend structure

```
src/
  pages/      Dashboard | DataImport | Accounts | Budgets | Forecasts | Variance
  features/
    import/   dropzone + per-row error report + template download
    grid/     TanStack Table editable accounts×periods grid (context selector)
    budgeting/ method wizard (Incremental/ABB/Value-Prop/ZBB) + modifier toggles + ZBB/Value-Prop scoring rubric
    forecasting/ series picker, model-override, point+interval chart, CV scoreboard
    variance/ side-by-side table + waterfall bridge + drill-down + materiality flags
  lib/        api client (TanStack Query), zod schemas (shared validation), money formatting (minor->display)
```

### 7.4 End-to-end request flows

**Forecast:** UI `POST /api/forecasts/run` → `auto_select`: clean/regularize series from `entries` (ACTUAL) → set `m`, gate seasonal models (≥2m heuristic + AICc/STL) → build candidate pool → `statsforecast.cross_validation` (rolling-origin) → rank by MASE → refit winner on full history → `forecast(h, level=[80,95])` conformal intervals → persist FORECAST rows + `forecast_runs` (selected_model, cv_mase) → return point/bands/scoreboard → UI renders line + shaded interval bands.

**Budget:** UI method wizard → `POST /api/budgets/run` → engine reads actuals + drivers (and packages/cap for ZBB/Value-Prop) → derive line amounts (per §2 formulas) → apply Flexible/Rolling modifiers → persist BUDGET rows under a new `budget_version` → return version for review/approval.

**Variance:** UI `POST /api/variance/compute` → build flexible budget at actual volume → compute Flex/Sales-Volume/price/mix/qty/cost variances → assert `Static = Flex + SalesVolume` → derive `is_favorable` from account type, `favorable_variance = variance × sign_factor` → apply configurable materiality dual-threshold → materialize `variance_results` → `GET /api/variance/bridge` returns order-averaged PVM waterfall → UI renders table + bridge + drill-down.

---

## 8. Phased Build Plan

**M0 — Scaffold (week 1).** Repo, FastAPI + Vite/React/TS skeleton, SQLite WAL, Alembic baseline, ruff/mypy/pytest + ESLint/Prettier/Vitest, **CI license gate**, NOTICE file.

**M1 — Data model & ingestion (weeks 2–3).** All tables + indexes + CHECK constraints. COA/dimensions/periods CRUD (fiscal-year config). WIDE+LONG upload parsing (calamine/openpyxl) → validation → pivot → UPSERT, with per-row error report. Template download endpoint. Manual-entry editable grid + change_log.

**M2 — Budgeting engines (weeks 4–6).** Four engines with the §2 formulas (worked examples as unit-test fixtures). Flexible-budget allowance + rolling scheduler modifiers. ZBB/Value-Prop decision-package model + scoring rubric + greedy/knapsack optimizer. Budget wizard UI.

**M3 — Forecasting engine (weeks 7–10).** Classic Tier-1 methods. statsforecast candidate pool, rolling-origin CV, MASE ranking, short-series fallback chain, seasonality gate (m + AICc/STL), conformal intervals + parametric fallback, per-series cache + CV scoreboard. Optional Prophet behind a feature flag (verify Windows install / Stan toolchain). Forecast UI with model override.

**M4 — Variance analysis (weeks 11–12).** Flexible-budget framework + master-hierarchy reconciliation assertion. All cost variances (correct FOH volume direction), sales price/volume, Horngren mix/qty. Sign engine + favorable-normalization. Configurable materiality. `variance_results` materialization.

**M5 — UI & visualization (weeks 13–15).** Dashboard; budget-vs-actual side-by-side table; variance bridge/waterfall (order-averaged PVM); forecast charts with interval bands; drill-down by all dimensions; CV scoreboard surfacing.

**M6 — Polish (weeks 16–17).** Playwright E2E, performance tuning (indexes, large imports via polars), error UX, copy-from seeding, docs (incl. the documented incremental-baseline choice and FOH-volume-artifact caveat), packaging for local single-user distribution.

---

## 9. Key Risks & Open Questions

**Risks**
- **Prophet install friction on Windows** (C++/Stan toolchain). Mitigation: keep Prophet optional behind a flag; statsforecast-only stack covers core needs. Ship a prebuilt wheel if adopted.
- **Short monthly FP&A series (<60 pts, often <24).** Many series will fall through the seasonal gate to naive/Holt/SES. Mitigation: treat the 2-cycle gate as a heuristic, lean on AICc/STL, surface "insufficient history" clearly.
- **Conformal calibration constraint** (`n_windows × h < series_length`) collides with short series. Mitigation: degrade to parametric intervals or fewer windows; never hide the degradation.
- **Wrong sales-mix formula creeping in** from AccountingTools. Mitigation: lock to Horngren formula with a reconciliation unit test (`Mix + Qty = Volume`).
- **Sign-convention bugs.** Mitigation: account-type-derived `is_favorable`, never sign alone; reconciliation assertions in CI.
- **License regression** via transitive npm/PyPI bumps. Mitigation: pinned versions + CI license gate.

**Open questions to confirm with product**
1. **Series characteristics** — monthly vs weekly vs daily, history length, number of distinct series — sets seasonal defaults, fallback thresholds, and whether numba-scale matters.
2. **Univariate vs driver-based** forecasting — driver models need SARIMAX-with-exog/scenario inputs and driver forecasts.
3. **Committed horizon/cadence** (e.g., rolling 12-month) — sets CV window size and minimum history.
4. **Costing basis default** for sales-volume/mix variances — contribution margin (recommended) vs gross profit vs revenue.
5. **Absorption vs variable costing** — determines whether the FOH volume variance and a denominator/normal-capacity level are needed.
6. **Material-price recognition** — at purchase (default) or usage.
7. **PVM interaction-term convention** — average across orders (recommended) vs fixed assignment.
8. **Static/Flexible/Rolling exposure** — user-visible modifiers vs sensible hidden defaults (e.g., always rolling-12, always flexible variable lines).
9. **Value-Prop/ZBB scoring inputs** — pure manual scores vs revenue-impact estimates vs weighted rubric; needs a guided wizard.
10. **Default user segment** (operational/manufacturing → ABB-heavy vs services/SaaS → Incremental + Value-Prop) — sets the default engine and cost-driver investment.
11. **ZBB-lite threshold** configuration.
12. **Multi-currency / FX, double-entry, BS+cash-flow, SCD-Type-2 dimensions, driver-based allocations, sub-month calendars** — all reserved in schema; confirm if any enter v1 scope.