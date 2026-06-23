"""Aggregate API router — included by app.main under the /api prefix."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    accounts,
    budgets,
    drivers,
    entries,
    forecasts,
    periods,
    reports,
    uploads,
    variance,
)

api_router = APIRouter()
api_router.include_router(accounts.router)
api_router.include_router(periods.router)
api_router.include_router(entries.router)
api_router.include_router(uploads.router)
api_router.include_router(budgets.router)
api_router.include_router(forecasts.router)
api_router.include_router(variance.router)
api_router.include_router(drivers.router)
api_router.include_router(reports.router)
