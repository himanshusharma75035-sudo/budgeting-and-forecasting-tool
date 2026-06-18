# Architecture

A visual tour of how the tool is put together. All diagrams are [Mermaid](https://mermaid.js.org/)
and render natively on GitHub.

- [System overview](#system-overview)
- [Request security pipeline](#request-security-pipeline)
- [Data model](#data-model)
- [Forecasting auto-selection](#forecasting-auto-selection)
- [Budgeting engine selection](#budgeting-engine-selection)
- [Variance analysis flow](#variance-analysis-flow)
- [Data ingestion pipeline](#data-ingestion-pipeline)
- [Combination space](#combination-space)

---

## System overview

```mermaid
flowchart TB
    subgraph Client["🖥️  Browser — React 19 SPA (Vite)"]
        UI["Pages: Dashboard · Budgets · Forecasts · Variance · Accounts · Data Import"]
        RQ["@tanstack/react-query cache"]
        UI --> RQ
    end

    RQ -->|"/api/* (proxied by Vite dev server)"| MW

    subgraph Backend["⚙️  FastAPI backend (Python)"]
        MW["Middleware stack<br/>(see Request security pipeline)"]
        subgraph Routes["API routes"]
            R1["accounts"]
            R2["budgets"]
            R3["forecasts"]
            R4["variance"]
            R5["entries / periods"]
            R6["uploads"]
        end
        MW --> Routes

        subgraph Domain["Domain layer (pure, unit-tested)"]
            D1["budgeting/<br/>4 engines + modifiers"]
            D2["forecasting/<br/>auto-select + intervals"]
            D3["variance/<br/>sign · PVM · bridge"]
            D4["ingestion/<br/>parse → validate → pivot"]
        end
        R2 --> D1
        R3 --> D2
        R4 --> D3
        R6 --> D4

        ORM["SQLModel / SQLAlchemy ORM"]
        Routes --> ORM
        Domain --> ORM
    end

    ORM -->|parameterized SQL| DB[("SQLite<br/>WAL · FK enforced")]
```

---

## Request security pipeline

Every request passes through defence-in-depth middleware before reaching a route. Starlette applies
the **last-added middleware outermost**, so the effective request order is:

```mermaid
flowchart LR
    Req(["Incoming request"]) --> CORS
    CORS["CORS<br/>origins pinned · no creds"] --> SH["Security headers<br/>CSP · nosniff · COOP/CORP"]
    SH --> TH["Trusted host<br/>allow-list"]
    TH --> RL["Rate limiter<br/>sliding window / IP"]
    RL --> BS["Body size cap<br/>≤ 25 MiB"]
    BS --> Route["Route handler"]
    Route --> Resp(["Response<br/>+ hardening headers"])

    TH -. "bad host" .-> R400(["400"])
    RL -. "over limit" .-> R429(["429 + Retry-After"])
    BS -. "too large" .-> R413(["413"])
```

See [`backend/app/security.py`](../backend/app/security.py) and [SECURITY.md](../SECURITY.md).

---

## Data model

A star-ish schema: postings (`Entry`) reference a chart of accounts and four dimensions, scoped by
scenario and optionally a budget version or forecast run.

```mermaid
erDiagram
    ACCOUNT   ||--o{ ENTRY : "posted to"
    PERIOD    ||--o{ ENTRY : "in"
    ENTITY    ||--o{ ENTRY : "dimension"
    DEPARTMENT||--o{ ENTRY : "dimension"
    PROJECT   ||--o{ ENTRY : "dimension"
    REGION    ||--o{ ENTRY : "dimension"
    BUDGET_VERSION ||--o{ ENTRY : "budget lines"
    FORECAST_RUN   ||--o{ ENTRY : "forecast points"

    ACCOUNT {
        int    account_id PK
        string account_code
        string account_name
        enum   account_type
        string account_category
        string normal_balance
        int    sign_factor
    }
    ENTRY {
        int    entry_id PK
        int    account_id FK
        int    period_key FK
        enum   scenario "ACTUAL|BUDGET|FORECAST"
        bigint amount_minor "integer paise"
        int    minor_unit_scale
        string currency
        int    budget_version_id FK
        int    forecast_run_id FK
    }
    PERIOD {
        int  period_key PK "YYYYMM"
        int  year
        int  month_num
        int  fiscal_year "Apr–Mar"
        int  fiscal_quarter
        bool is_closed
    }
    BUDGET_VERSION {
        int    budget_version_id PK
        string name
        int    fiscal_year
        enum   method
    }
    FORECAST_RUN {
        int    forecast_run_id PK
        string selected_model
        int    horizon
    }
```

Money is stored as **integer minor units** (paise) and computed in `Decimal` — never `float`.

---

## Forecasting auto-selection

Each series is forecast by the model that wins a **rolling-origin backtest**, ranked on **MASE**,
then wrapped with prediction intervals.

```mermaid
flowchart TD
    H["Account history<br/>(actuals or inline series)"] --> S{"Seasonality gate<br/>≥ 2 cycles?"}
    S -->|yes| Pool["Candidate pool"]
    S -->|no| Pool

    subgraph Pool["Candidate model pool"]
        B["Baselines:<br/>naive · seasonal-naive · drift ·<br/>window/moving average"]
        C["Classic FP&A:<br/>straight-line · linear regression"]
        A["Optional (extra):<br/>AutoARIMA · AutoETS ·<br/>AutoTheta · AutoCES · Prophet"]
    end

    Pool --> CV["Rolling-origin cross-validation"]
    CV --> Score["Score each model<br/>MASE · RMSE · MAE"]
    Score --> Pick["Pick lowest MASE<br/>(or user override)"]
    Pick --> Fit["Refit on full history"]
    Fit --> PI["Conformal prediction intervals<br/>(80 / 90 / 95%)"]
    PI --> Out["Point forecast + fan chart + scoreboard"]
```

---

## Budgeting engine selection

Four derivation engines are wrapped by two orthogonal modifiers — **volume** (static vs flexible)
and **cadence** (periodic vs rolling).

```mermaid
flowchart TD
    Req["Budget run request"] --> M{"method?"}
    M -->|INCREMENTAL| E1["prior actual × (1 + growth) + one-offs"]
    M -->|ACTIVITY_BASED| E2["cost pools × driver rates × volume"]
    M -->|VALUE_PROPOSITION| E3["rank by value/cost,<br/>fund under cap (greedy / knapsack)"]
    M -->|ZERO_BASED| E4["build up from decision packages"]

    E1 --> V
    E2 --> V
    E3 --> V
    E4 --> V

    V{"volume mode"} -->|STATIC| C
    V -->|FLEXIBLE| Flex["flex to actual activity"] --> C
    C{"cadence"} -->|PERIODIC| Out["Budget version + lines"]
    C -->|ROLLING| Roll["roll forward horizon"] --> Out
```

---

## Variance analysis flow

```mermaid
flowchart TD
    A["Actual entries"] --> Agg["Aggregate by (account, period)<br/>scoped to comparison scenario"]
    B["Budget / forecast entries"] --> Agg
    Agg --> Calc["Per-account variance<br/>= actual − comparison"]
    Calc --> Sign["Sign engine<br/>(favorable / unfavorable by account type)"]
    Sign --> Mat["Materiality test<br/>(% and absolute thresholds)"]
    Sign --> PVM["Price · Volume · Mix · Efficiency<br/>decomposition"]
    Sign --> Bridge["IBCS waterfall bridge<br/>grouped by Schedule III category"]
    Mat --> Table["Variance table"]
    PVM --> Table
    Bridge --> Chart["Waterfall chart"]
```

---

## Data ingestion pipeline

```mermaid
flowchart LR
    F["Upload CSV / Excel<br/>(wide or long)"] --> P["Parse"]
    P --> Det{"layout?"}
    Det -->|WIDE| Pivot["Pivot wide → long"]
    Det -->|LONG| Val
    Pivot --> Val["Validate<br/>(accounts, periods, dims, amounts)"]
    Val -->|ok rows| Up["Upsert entries<br/>(integer minor units)"]
    Val -->|rejected rows| Rep["Error report<br/>(row, reason)"]
    Up --> Rep
    Rep --> Resp(["UploadReport:<br/>total / ok / rejected / inserted"])
```

---

## Combination space

The selectable options multiply into a large, well-defined space — enumerated in
[COMBINATIONS.md](COMBINATIONS.md).

```mermaid
flowchart LR
    subgraph Budgeting["Budgeting — 16"]
        b1["4 methods"] --- b2["× Static/Flexible"] --- b3["× Periodic/Rolling"]
    end
    subgraph Forecasting["Forecasting — 28"]
        f1["model pool"] --- f2["× seasonality"] --- f3["× interval levels"]
    end
    subgraph Variance["Variance — 84"]
        v1["scenario pairs"] --- v2["× decomposition"] --- v3["× scope"]
    end
```
