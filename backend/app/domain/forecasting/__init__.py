"""Forecasting engine (DESIGN.md section 3).

Two-tier model menu with an autonomous selector: explainable Tier-1 classics
(:mod:`classic`) plus naive baselines (:mod:`baselines`), scored by rolling-origin CV
on MASE and wrapped in distribution-free conformal intervals. Pure-numpy core;
statsforecast/statsmodels are optional and import-guarded.
"""

from __future__ import annotations

from . import baselines, classic, metrics
from .auto_select import (
    ForecastResult,
    ModelScore,
    auto_forecast,
    default_candidates,
    rolling_origin_cv,
)

__all__ = [
    "auto_forecast",
    "ForecastResult",
    "ModelScore",
    "default_candidates",
    "rolling_origin_cv",
    "metrics",
    "classic",
    "baselines",
]
