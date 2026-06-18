"""Distribution-free conformal prediction intervals (DESIGN.md 3.5).

The default interval method calibrates on cross-validation residuals: the half-width at
level ``L`` is the ``L``-th percentile of the absolute residuals, so higher levels are
naturally nested (80% subset of 95%). Empirical coverage should be validated against the
nominal level on CV windows.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import numpy as np
from numpy.typing import ArrayLike


def conformal_intervals(
    point: np.ndarray,
    residuals: ArrayLike,
    levels: Iterable[int],
) -> tuple[dict[int, list[float]], dict[int, list[float]]]:
    """Build nested conformal intervals around ``point`` (DESIGN.md 3.5).

    Args:
        point: point forecast, length ``h``.
        residuals: flat 1-D array/list of CV residuals (errors ``y - yhat``).
        levels: confidence levels in percent (e.g. ``(80, 95)``).

    Returns:
        ``(lower, upper)`` dicts keyed by integer level. For each level ``L`` the
        half-width is ``q = quantile(|residuals|, L/100)`` (0 when no residuals), giving
        ``lower[L] = point - q`` and ``upper[L] = point + q``. Higher levels are wider,
        so the intervals are nested.
    """
    point = np.asarray(point, dtype=float).ravel()
    abs_resid = np.abs(np.asarray(residuals, dtype=float).ravel())

    lower: dict[int, list[float]] = {}
    upper: dict[int, list[float]] = {}
    for level in levels:
        lvl = int(level)
        if abs_resid.size == 0:
            q = 0.0
        else:
            q = float(np.quantile(abs_resid, lvl / 100.0))
        lower[lvl] = [float(v) for v in (point - q)]
        upper[lvl] = [float(v) for v in (point + q)]
    return lower, upper


def empirical_coverage(
    y_true: ArrayLike, lower: Sequence[float], upper: Sequence[float]
) -> float:
    """Fraction of actuals falling within ``[lower, upper]`` (DESIGN.md 3.5).

    Returns ``nan`` for an empty input so callers can distinguish "no data" from 0%.
    """
    y_true = np.asarray(y_true, dtype=float).ravel()
    lo = np.asarray(lower, dtype=float).ravel()
    hi = np.asarray(upper, dtype=float).ravel()
    if y_true.size == 0:
        return float("nan")
    inside = (y_true >= lo) & (y_true <= hi)
    return float(np.mean(inside))
