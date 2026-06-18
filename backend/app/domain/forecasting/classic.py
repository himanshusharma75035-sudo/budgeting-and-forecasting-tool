"""Tier-1 explainable classic FP&A forecasters (DESIGN.md 3.1).

These are the methods finance teams trust and audit (straight-line/growth-rate, moving
average, simple/multiple linear regression). Each single-series function takes a 1-D
history and horizon ``h`` and returns an ``np.ndarray`` of length ``h``.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike

from .baselines import naive


def _as_float_array(x: ArrayLike) -> np.ndarray:
    return np.asarray(x, dtype=float).ravel()


def straight_line(history: ArrayLike, h: int) -> np.ndarray:
    """Growth-rate / straight-line extrapolation (DESIGN.md 3.1).

    ``g = (V_t - V_{t-1}) / V_{t-1}``; ``F_k = V_t * (1 + g)**k`` for ``k = 1..h``.
    Falls back to :func:`naive` when there are fewer than 2 points or the prior value
    is zero (growth rate undefined).
    """
    history = _as_float_array(history)
    if history.size < 2:
        return naive(history, h)
    last = history[-1]
    prev = history[-2]
    if prev == 0.0:
        return naive(history, h)
    g = (last - prev) / prev
    k = np.arange(1, h + 1, dtype=float)
    return last * (1.0 + g) ** k


def moving_average(history: ArrayLike, h: int, window: int = 3) -> np.ndarray:
    """Flat forecast equal to the mean of the last ``window`` observations (DESIGN.md 3.1)."""
    history = _as_float_array(history)
    if history.size == 0:
        return np.zeros(h, dtype=float)
    w = min(window, history.size)
    value = float(np.mean(history[-w:]))
    return np.full(h, value, dtype=float)


def simple_linear_regression(history: ArrayLike, h: int) -> np.ndarray:
    """OLS of value on time index (DESIGN.md 3.1): ``Y = mX + c``.

    Fits a degree-1 polynomial on indices ``0..n-1`` and extrapolates to indices
    ``n..n+h-1``. Falls back to :func:`naive` for fewer than 2 points.
    """
    history = _as_float_array(history)
    n = history.size
    if n < 2:
        return naive(history, h)
    x = np.arange(n, dtype=float)
    slope, intercept = np.polyfit(x, history, deg=1)
    future_x = np.arange(n, n + h, dtype=float)
    return slope * future_x + intercept


def multiple_linear_regression(
    y: ArrayLike, X: ArrayLike, X_future: ArrayLike
) -> np.ndarray:
    """Multiple OLS with intercept (DESIGN.md 3.1): ``Y = b0 + b1 X1 + ... + bk Xk``.

    Args:
        y: training target, shape ``(n,)``.
        X: training drivers, shape ``(n, k)``.
        X_future: future driver values, shape ``(h, k)``.

    Returns predictions for ``X_future`` (length ``h``). Drivers must themselves be
    forecast/supplied (DESIGN.md 3.1); multicollinearity is the caller's concern.
    """
    y = _as_float_array(y)
    X = np.asarray(X, dtype=float)
    X_future = np.asarray(X_future, dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    if X_future.ndim == 1:
        X_future = X_future.reshape(-1, 1)

    n = X.shape[0]
    A = np.column_stack([np.ones(n), X])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)

    A_future = np.column_stack([np.ones(X_future.shape[0]), X_future])
    return A_future @ coef
