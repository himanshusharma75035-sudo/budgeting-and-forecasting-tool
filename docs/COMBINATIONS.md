# Budgeting × Forecasting × Variance — the combination space

How many distinct configurations the tool can produce. The three engines **compose as a
pipeline** (forecast → budget → variance); they don't collapse into one number, so the counts
below are given per engine and then as the coupled space.

---

## 1. Budgeting

Three orthogonal axes (see [DESIGN.md §2](DESIGN.md)):

| Axis | Options | Count |
|---|---|---|
| **Derivation engine** (how each line is derived) | Incremental · Activity-Based · Value-Proposition · Zero-Based | 4 |
| **Volume mode** (how it responds to actual volume) | Static · Flexible | 2 |
| **Cadence** (how it re-extends in time) | Periodic (annual) · Rolling(horizon) | 2 |

- **Core budgeting configurations = 4 × 2 × 2 = `16`.**
- Counting common rolling horizons (12 / 18 / 24 months) as variants of the rolling branch:
  4 × 2 × (1 periodic + 3 rolling) = **`32`**.

Examples the matrix yields: *Static Periodic Incremental* (the classic annual budget),
*Flexible Rolling-12 ABB*, *Static Periodic Zero-Based*, etc.

---

## 2. Forecasting (per series)

The engine auto-selects from a candidate pool by backtested MASE; you can also pin a model.

| Axis | Options | Count |
|---|---|---|
| **Model pool — always on** (pure-numpy) | Naive, Seasonal-Naive, Drift, Window-Average, Moving-Average, Straight-line/Growth, Simple Linear Reg., Multiple Linear Reg. | 8 |
| **Model pool — optional `forecasting` extra** | AutoARIMA (SARIMA), AutoETS (Holt-Winters), AutoTheta, AutoCES, Prophet | +5 |
| **Selection mode** | Auto-select · Manual override | — |
| **Input mode** | Univariate · Driver-based (exogenous regressors) | 2 |
| **Prediction-interval levels** | any non-empty subset of {80, 90, 95, 99} | 2⁴−1 = 15 |
| **Horizon** | 6 / 12 / 18 / 24 … | open |
| **Seasonal period m** | auto-detected: 1 (none), 4 (qtr), 12 (monthly), 52 (weekly)… | data-driven |

- Model **choices** per series = 1 *Auto* + up to 13 manual = **up to `14`**.
- "Method configurations" = model choice × input mode = 14 × 2 = **`28`**.
- Fully parameterized (× interval-level set) = 28 × 15 = **`420`** per series; × 4 horizons = **`1,680`**.
- Across the workspace these are *per series* — with N forecastable accounts the live space is ×N.

---

## 3. Variance (consumes the outputs of the other two)

| Axis | Options | Count |
|---|---|---|
| **Scenario pair** (base vs compare) | from {Actual, Budget, Forecast} | 3 unordered / 6 ordered |
| **Variance kind** | Budget-vs-Actual, Flexible-budget, Sales-Volume, Sales-Price, Sales-Mix, Sales-Quantity, Material-Price, Material-Quantity, Labour-Rate, Labour-Efficiency, VOH-Spending, VOH-Efficiency, FOH-Spending, FOH-Volume | 14 |
| **Slice / drill-down** | entity × department × project × region × period grain | multiplicative |

- Variance **views** = 6 scenario pairs × 14 kinds = **`84`** (before dimension slicing).

---

## 4. The coupled (pipeline) space

The engines feed each other, so the headline numbers are:

| Stage | Practical (bounded) | Parameterized max |
|---|---|---|
| Budgeting | **16** | 32 (with rolling horizons) |
| Forecasting (per series) | **28** | 1,680 |
| Variance | **84** | × dimension slices |

**Forecast-driven budgets.** The two engines that consume forecasts as drivers (Incremental
growth %, ABB volumes) can be seeded by *any* forecast. That coupling =
`(2 engines × 2 volume × 2 cadence) × 28 forecast configs = 8 × 28 = 224` forecast-driven
budget combinations (× rolling horizons → larger). The other two engines
(Value-Proposition, Zero-Based) take judgement inputs rather than forecasts, so they sit outside
this product.

**Bottom line.** ~**16 budgeting** × ~**28 forecasting** method configs, joined by ~**84 variance**
views — a few hundred *practical* end-to-end combinations, expanding into the thousands once
interval-level sets, horizons, seasonal periods, and dimension slices are parameterized.

---

## 5. Implementation status

| Capability | Status |
|---|---|
| 4 budgeting engines | ✅ implemented + unit-tested |
| Static/Flexible volume mode, Periodic/Rolling cadence | ✅ in API + UI selectors; flexible-allowance & rolling-horizon helpers implemented |
| Forecasting pool (8 always-on) + Auto-select by MASE | ✅ implemented + tested |
| Advanced models (ARIMA/ETS/Theta/CES/Prophet) | ✅ wired behind the optional `forecasting` extra |
| Manual model override · interval-level sets · horizon | ✅ exposed in the Forecasts UI |
| Driver-based (exogenous) forecasting | ⏳ engine supports MLR/SARIMAX-exog; UI for drivers is planned |
| Variance: budget-vs-actual, sign engine, PVM bridge | ✅ implemented + tested |
| Full cost/sales variance decomposition (mix/qty/price/efficiency) | ✅ formulas implemented + tested; dedicated UI surfaces planned |
| Dimension drill-down (dept/region/project) | ⏳ data model + dimensions seeded; drill-down UI planned |
