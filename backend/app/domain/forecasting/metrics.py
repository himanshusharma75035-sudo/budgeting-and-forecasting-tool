"""Forecast accuracy metrics (DESIGN.md 3.3).

All functions accept 1-D numpy float arrays (or array-likes) and return Python floats.
MASE is the *primary* selection metric (scale-invariant, defined for zero/intermittent
data). sMAPE is for display only and must never drive ranking (Hyndman & Koehler).
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike


def _as_float_array(x: ArrayLike) -> np.ndarray:
    return np.asarray(x, dtype=float).ravel()


def mae(y_true: ArrayLike, y_pred: ArrayLike) -> float:
    """Mean absolute error: ``mean(|y - yhat|)``."""
    y_true = _as_float_array(y_true)
    y_pred = _as_float_array(y_pred)
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true: ArrayLike, y_pred: ArrayLike) -> float:
    """Root mean squared error: ``sqrt(mean((y - yhat)**2))``."""
    y_true = _as_float_array(y_true)
    y_pred = _as_float_array(y_pred)
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def mape(y_true: ArrayLike, y_pred: ArrayLike) -> float:
    """Mean absolute percentage error: ``100 * mean(|e / y|)``.

    Computed only over positions where ``y_true != 0`` (undefined/explosive near zero;
    DESIGN.md 3.3). If no position has a non-zero actual, returns ``nan``.
    """
    y_true = _as_float_array(y_true)
    y_pred = _as_float_array(y_pred)
    mask = y_true != 0.0
    if not np.any(mask):
        return float("nan")
    return float(100.0 * np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])))


def smape(y_true: ArrayLike, y_pred: ArrayLike) -> float:
    """Symmetric MAPE: ``mean(200 * |y - yhat| / (|y| + |yhat|))``.

    Display only -- never use for ranking (DESIGN.md 3.3). Positions where both actual
    and prediction are zero contribute 0 (guard against 0/0).
    """
    y_true = _as_float_array(y_true)
    y_pred = _as_float_array(y_pred)
    denom = np.abs(y_true) + np.abs(y_pred)
    numer = 200.0 * np.abs(y_true - y_pred)
    contributions = np.divide(
        numer, denom, out=np.zeros_like(denom), where=denom != 0.0
    )
    return float(np.mean(contributions))


def mase(y_true: ArrayLike, y_pred: ArrayLike, y_train: ArrayLike, m: int = 1) -> float:
    """Mean absolute scaled error (DESIGN.md 3.3) -- the primary selection metric.

    ``MASE = mean(|e_t|) / Q`` where the scaling denominator ``Q`` is the in-sample
    mean absolute error of the (seasonal) naive forecast on the training series::

        Q = mean(|y_train[t] - y_train[t - m]|)  for t in [m, len(y_train))

    ``m >= 1`` (``m == 1`` is the non-seasonal naive denominator). Returns ``nan`` when
    the denominator is zero or non-finite (e.g. a flat training series).
    """
    if m < 1:
        raise ValueError(f"m must be >= 1, got {m}")
    y_true = _as_float_array(y_true)
    y_pred = _as_float_array(y_pred)
    y_train = _as_float_array(y_train)

    if y_train.size <= m:
        return float("nan")
    diffs = np.abs(y_train[m:] - y_train[:-m])
    denom = float(np.mean(diffs))
    if denom == 0.0 or not np.isfinite(denom):
        return float("nan")
    return float(np.mean(np.abs(y_true - y_pred)) / denom)
