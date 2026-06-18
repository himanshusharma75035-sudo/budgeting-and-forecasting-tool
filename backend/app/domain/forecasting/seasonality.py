"""Seasonality detection & gating (DESIGN.md 3.2 / 3.4).

Seasonal period ``m`` is set a priori by calendar; the 2-cycle gate is a pragmatic
product heuristic (NOT Hyndman-endorsed theory, DESIGN.md 3.4). STL strength-of-
seasonality ``Fs`` is an additional gate when statsmodels is available; otherwise we
fall back to lag-``m`` autocorrelation. statsmodels is optional and import-guarded.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike


def infer_seasonal_period(freq: str) -> int:
    """Map a pandas-style frequency string to a seasonal period ``m`` (DESIGN.md 3.2).

    Monthly -> 12, quarterly -> 4, weekly -> 52, daily -> 7; otherwise 1 (non-seasonal).
    """
    if not freq:
        return 1
    key = str(freq).strip().upper()
    mapping = {
        "M": 12,
        "MS": 12,
        "ME": 12,
        "Q": 4,
        "QS": 4,
        "QE": 4,
        "W": 52,
        "D": 7,
    }
    return mapping.get(key, 1)


def allow_seasonal(n: int, m: int, min_cycles: int = 2) -> bool:
    """Short-series gate (DESIGN.md 3.4): allow seasonal models only when enough cycles.

    True iff ``m > 1`` and ``n >= min_cycles * m``.
    """
    return m > 1 and n >= min_cycles * m


def seasonal_strength(history: ArrayLike, m: int) -> float:
    """STL strength-of-seasonality ``Fs`` (DESIGN.md 3.2), clipped to ``[0, 1]``.

    ``Fs = max(0, 1 - Var(R_t) / Var(S_t + R_t))`` from an STL decomposition (period
    ``m``) when statsmodels is available. Otherwise falls back to the absolute lag-``m``
    autocorrelation clipped to ``[0, 1]``. Returns 0.0 for a non-seasonal period or
    insufficient data.
    """
    series = np.asarray(history, dtype=float).ravel()
    n = series.size
    if m < 2 or n < 2 * m:
        return 0.0

    try:
        from statsmodels.tsa.seasonal import STL  # type: ignore

        result = STL(series, period=m, robust=True).fit()
        resid = np.asarray(result.resid, dtype=float)
        seasonal = np.asarray(result.seasonal, dtype=float)
        var_resid = float(np.var(resid))
        var_seasonal_resid = float(np.var(seasonal + resid))
        if var_seasonal_resid == 0.0 or not np.isfinite(var_seasonal_resid):
            return 0.0
        return float(max(0.0, 1.0 - var_resid / var_seasonal_resid))
    except Exception:
        return _autocorr_strength(series, m)


def _autocorr_strength(series: np.ndarray, m: int) -> float:
    """Fallback: |autocorrelation| at lag ``m`` clipped to ``[0, 1]``."""
    if series.size <= m:
        return 0.0
    centered = series - series.mean()
    denom = float(np.sum(centered * centered))
    if denom == 0.0 or not np.isfinite(denom):
        return 0.0
    numer = float(np.sum(centered[m:] * centered[:-m]))
    return float(np.clip(abs(numer / denom), 0.0, 1.0))
