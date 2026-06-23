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

    # --- HTTP hardening (see app/security.py and SECURITY.md) ---
    # Host header allow-list (anti DNS-rebinding / host-spoofing). "testserver" is the host the
    # TestClient uses; it is not routable so leaving it in is harmless for a local-first tool.
    trusted_hosts: list[str] = ["localhost", "127.0.0.1", "testserver"]
    # Request body cap — generous enough for CSV/Excel template uploads, but bounds memory use.
    max_request_bytes: int = 25 * 1024 * 1024  # 25 MiB
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 240
    # Enable only when the API is served behind HTTPS/TLS (HSTS over plain HTTP is harmful).
    enable_hsts: bool = False
    # CSP is tuned so the bundled Swagger UI (/docs) still loads from the jsDelivr CDN while
    # everything else is locked to 'self'. The SPA is served separately by Vite/its own host.
    content_security_policy: str = (
        "default-src 'self'; "
        "img-src 'self' data: https://fastapi.tiangolo.com; "
        "script-src 'self' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "worker-src 'self' blob:; connect-src 'self'; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'"
    )
    permissions_policy: str = "geolocation=(), microphone=(), camera=(), payment=(), usb=()"

    # --- Optional AI assist (off by default; the tool stays fully offline/self-hostable) ---
    # Enable with OPENFPA_AI_ENABLED=true and OPENFPA_ANTHROPIC_API_KEY=... plus the [ai] extra.
    ai_enabled: bool = False
    anthropic_api_key: str = ""
    ai_model: str = "claude-opus-4-8"

    # Forecasting defaults
    default_forecast_horizon: int = 12
    default_cv_windows: int = 3
    seasonal_min_cycles: int = 2  # heuristic gate; see DESIGN.md 3.4


settings = Settings()
DATA_DIR.mkdir(parents=True, exist_ok=True)
