# OpenFP&A — Budgeting & Forecasting Tool

A **local-first, single-user** open-source FP&A tool that unifies three things no single
open-source tool offers together:

1. **Four corporate budgeting methods** — Incremental, Activity-Based (ABB),
   Value-Proposition (Priority-Based), and Zero-Based (ZBB) — as selectable derivation
   engines, wrapped by orthogonal **Static/Flexible** and **Periodic/Rolling** modifiers.
2. **Autonomous statistical forecasting** — auto-selected ARIMA/SARIMA, ETS/Holt-Winters,
   Theta/CES and Prophet (plus transparent classic FP&A methods), chosen per series by
   **rolling-origin backtesting** ranked on **MASE**, with prediction intervals.
3. **Rigorous variance analysis** — budget-vs-actual plus full price / volume / mix /
   efficiency decomposition, with a sign-safe favorable/unfavorable engine and a waterfall
   bridge.

Data goes in **manually** (editable accounts × periods grid) or via **CSV/Excel template
upload** (wide or long layout).

> **License posture:** the distributable is **MIT**, and every dependency is OSI-permissive
> (MIT / BSD / Apache-2.0). A CI license gate fails the build on any GPL/AGPL/SSPL/BSL or
> commercial dependency. See [NOTICE](NOTICE).

## Documentation

- **[docs/DESIGN.md](docs/DESIGN.md)** — the implementation-ready build brief (the four
  budgeting algorithms, the forecasting auto-selection pipeline, the *verified* variance
  formulas, the data model, the stack, and the phased plan).
- **[docs/RESEARCH_APPENDIX.md](docs/RESEARCH_APPENDIX.md)** — raw research dossiers, the
  adversarial verification verdicts, and all 169 cited sources.

## Repository layout

```
backend/    FastAPI + SQLite (the FP&A engine lives here)
  app/
    api/routes/     HTTP endpoints
    db/             SQLModel models + session (SQLite, WAL)
    domain/
      budgeting/    4 engines + Static/Flexible + Rolling modifiers
      forecasting/  classic methods, baselines, metrics, rolling-origin auto-select, intervals
      variance/     sign engine, budget-vs-actual, cost & sales variances, materiality, bridge
      ingestion/    upload parse -> validate -> pivot wide->long -> upsert
  tests/            unit tests (the DESIGN.md worked examples are the fixtures)
frontend/   React + Vite + TypeScript SPA
docs/       design brief, research appendix, upload templates
```

## Quick start

> On Windows `cmd`/PowerShell, run each command on its own line — don't paste a trailing
> `# comment`, since `#` is not a comment marker there and gets passed to the program.

### Backend

```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python scripts/seed.py
uvicorn app.main:app --reload --reload-dir app
```

- macOS/Linux: activate with `source .venv/bin/activate`.
- Add the heavy statistical models with `pip install -e ".[dev,forecasting]"`.
- `pytest` runs the tests. API at http://127.0.0.1:8000 , docs at `/docs`.
- **`--reload-dir app` is important:** plain `--reload` watches `.venv` too, and if the project is
  in a synced folder (Dropbox/OneDrive), the sync churn makes uvicorn reload endlessly. Scoping to
  `app` fixes it; `uvicorn app.main:app` with no reload also works.

### Frontend

```
cd frontend
npm install
npm run dev
```

Dev server at http://127.0.0.1:5173, proxying `/api` to the backend on port 8000.

## Status

This is the **scaffold + research** deliverable. The deterministic FP&A logic (all four
budgeting engines, the variance formulas, the classic forecasting methods + naive baselines +
metrics + rolling-origin auto-selection) is **implemented and unit-tested**. The heavy
statistical models (statsforecast / Prophet) sit behind an optional `forecasting` extra with a
clean interface, and the React UI is a routable skeleton wired to the API. See the phased plan
(M0–M6) in [docs/DESIGN.md](docs/DESIGN.md#8-phased-build-plan).
