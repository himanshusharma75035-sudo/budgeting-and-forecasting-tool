"""Naive baseline forecasters (DESIGN.md 3.4).

These double as the MASE denominators and as the short-series fallback. Each function
takes a 1-D history array and an integer horizon ``h`` and returns an ``np.ndarray`` of
length ``h``.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike


def _as_float_array(x: ArrayLike) -> np.ndarray:
    return np.asarray(x, dtype=float).ravel()


def naive(history: ArrayLike, h: int) -> np.ndarray:
    """Repeat the last observed value: ``yhat_{t+k} = y_t`` (DESIGN.md 3.4)."""
    history = _as_float_array(history)
    if history.size == 0:
        return np.zeros(h, dtype=float)
    return np.full(h, history[-1], dtype=float)


def seasonal_naive(history: ArrayLike, h: int, m: int) -> np.ndarray:
    """Tile the last ``m`` observations forward: ``yhat_{t+h} = y_{t+h-m(k+1)}``.

    Falls back to :func:`naive` when fewer than ``m`` points are available or ``m < 1``.
    """
    history = _as_float_array(history)
    if m < 1 or history.size < m:
        return naive(history, h)
    last_cycle = history[-m:]
    reps = int(np.ceil(h / m))
    tiled = np.tile(last_cycle, reps)
    return tiled[:h].astype(float)


def drift(history: ArrayLike, h: int) -> np.ndarray:
    """Linear drift through first and last points (DESIGN.md 3.4).

    ``yhat_{t+k} = y_t + k * (y_t - y_1) / (n - 1)`` for ``k = 1..h``. Needs ``n >= 2``;
    otherwise degrades to :func:`naive`.
    """
    history = _as_float_array(history)
    n = history.size
    if n < 2:
        return naive(history, h)
    slope = (history[-1] - history[0]) / (n - 1)
    k = np.arange(1, h + 1, dtype=float)
    return history[-1] + k * slope


def window_average(history: ArrayLike, h: int, window: int = 3) -> np.ndarray:
    """Flat forecast equal to the mean of the last ``window`` observations."""
    history = _as_float_array(history)
    if history.size == 0:
        return np.zeros(h, dtype=float)
    w = min(window, history.size)
    value = float(np.mean(history[-w:]))
    return np.full(h, value, dtype=float)
