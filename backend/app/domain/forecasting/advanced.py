"""Tier-2 autonomous statistical models via statsforecast (DESIGN.md 3.1 / 3.2).

statsforecast (and numba) is an *optional* heavy dependency. Everything here is
best-effort and import-guarded: if the library is missing or anything raises while
building/calling a model, we degrade to the naive baseline and never propagate the
exception. The engine works with numpy alone when statsforecast is unavailable.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from .baselines import naive

ModelFn = Callable[[np.ndarray, int], np.ndarray]


def statsforecast_available() -> bool:
    """True iff statsforecast can be imported."""
    try:
        import statsforecast  # noqa: F401

        return True
    except Exception:
        return False


def advanced_models(m: int) -> dict[str, ModelFn]:
    """Build single-series statsforecast callables keyed by model name (DESIGN.md 3.1).

    Returns a dict mapping ``{"AutoARIMA", "AutoETS", "AutoTheta"}`` to callables
    ``fn(history, h) -> np.ndarray`` with ``season_length=m``. Returns ``{}`` on any
    ImportError/Exception. Each callable is self-contained and defensively falls back to
    :func:`naive` if fitting/predicting fails.
    """
    try:
        from statsforecast.models import AutoARIMA, AutoETS, AutoTheta  # type: ignore
    except Exception:
        return {}

    season_length = max(1, int(m))

    def _make(model_cls: type) -> ModelFn:
        def _fn(history: np.ndarray, h: int) -> np.ndarray:
            try:
                series = np.asarray(history, dtype=float).ravel()
                if series.size < 2:
                    return naive(series, h)
                model = model_cls(season_length=season_length)
                fitted = model.fit(series)
                out = fitted.predict(h=h)
                mean = np.asarray(out["mean"], dtype=float).ravel()
                if mean.size < h or not np.all(np.isfinite(mean)):
                    return naive(series, h)
                return mean[:h]
            except Exception:
                return naive(history, h)

        return _fn

    try:
        return {
            "AutoARIMA": _make(AutoARIMA),
            "AutoETS": _make(AutoETS),
            "AutoTheta": _make(AutoTheta),
        }
    except Exception:
        return {}
