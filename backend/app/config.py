"""Application settings (env-overridable)."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OPENFPA_", env_file=".env", extra="ignore")

    # One SQLite file per workspace (local-first).
    database_url: str = f"sqlite:///{(DATA_DIR / 'openfpa.db').as_posix()}"

    # Workspace defaults (Indian standards)
    base_currency: str = "INR"
    minor_unit_scale: int = 2  # paise
    fiscal_year_start_month: int = 4  # Indian fiscal year: April–March

    # CORS for the Vite dev server
    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]

    # Forecasting defaults
    default_forecast_horizon: int = 12
    default_cv_windows: int = 3
    seasonal_min_cycles: int = 2  # heuristic gate; see DESIGN.md 3.4


settings = Settings()
DATA_DIR.mkdir(parents=True, exist_ok=True)
