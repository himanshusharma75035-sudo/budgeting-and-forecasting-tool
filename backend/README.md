# OpenFP&A — Backend

FastAPI + SQLite. All FP&A logic lives in `app/domain/` as pure, unit-tested Python.

## Setup

Run each line on its own (do not paste trailing `#` comments into Windows `cmd`/PowerShell —
they are not comment markers there and will be passed to the program as arguments).

Windows (`cmd` / PowerShell):

```
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python scripts/seed.py
uvicorn app.main:app --reload --reload-dir app
```

macOS / Linux:

```
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python scripts/seed.py
uvicorn app.main:app --reload --reload-dir app
```

- API at http://127.0.0.1:8000 , interactive docs at `/docs`.
- `pip install -e ".[dev,forecasting]"` adds the optional heavy models (statsforecast / Prophet).
- `pytest` runs the tests; `ruff check .` and `mypy app` lint/type-check.

> **Why `--reload-dir app`?** Plain `--reload` watches the whole `backend/` folder, including the
> 300 MB `.venv`. If the project sits in a synced folder (Dropbox/OneDrive/Google Drive), the sync
> client constantly touches files in `.venv`, which makes uvicorn reload in an endless loop.
> Scoping the watcher to `app` (your source) fixes it. Plain `uvicorn app.main:app` (no reload)
> also works. Better still: keep the virtualenv **outside** the synced folder.

## Layout

| Path | Responsibility |
|---|---|
| `app/domain/budgeting/` | Incremental, ABB, Value-Proposition, ZBB engines + Static/Flexible/Rolling modifiers |
| `app/domain/forecasting/` | metrics, classic methods, baselines, seasonality, rolling-origin auto-select, intervals |
| `app/domain/variance/` | sign engine, budget-vs-actual, cost & sales variances, materiality, PVM bridge |
| `app/domain/ingestion/` | upload parse → validate → pivot wide↔long |
| `app/db/` | SQLModel models + SQLite session (WAL) |
| `app/api/routes/` | thin HTTP endpoints mapping DTOs ↔ domain |
| `tests/` | the DESIGN.md worked examples as fixtures |

## Notes

- **Money** is stored as integer minor units (`amount_minor`); domain math uses `Decimal`.
- **Migrations:** Alembic is configured (`alembic revision --autogenerate -m "baseline"`),
  but for local dev `init_db()` (create_all) runs on startup.
- The heavy forecasting libraries are optional; without them the engine still runs the classic
  FP&A methods + naive baselines and auto-selects among them by backtested MASE.
