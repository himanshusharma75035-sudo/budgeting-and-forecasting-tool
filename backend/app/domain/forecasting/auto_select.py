"""Autonomous forecast model selection (DESIGN.md 3.2 -- the autonomous core).

Pipeline per series: detect seasonal period ``m`` from the calendar frequency, gate
seasonal models by the short-series heuristic (DESIGN.md 3.4), build a candidate pool,
score with rolling-origin cross-validation (NOT random k-fold -- that leaks future into
past), select the lowest-MASE model, refit the winner on full history, and emit
conformal prediction intervals from the winner's CV residuals (DESIGN.md 3.5).

The engine never raises on bad/short input: it degrades to the naive baseline.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from functools import partial

import numpy as np
from numpy.typing import ArrayLike

from . import baselines, classic
from .advanced import advanced_models
from .intervals import conformal_intervals
from .seasonality import allow_seasonal as allow_seasonal_fn
from .seasonality import infer_seasonal_period

CandidateFn = Callable[[np.ndarray, int], np.ndarray]


@dataclass
class ModelScore:
    """Cross-validated scoreboard row for one candidate model."""

    model: str
    mase: float
    rmse: float
    mae: float


@dataclass
class ForecastResult:
    """Output of :func:`auto_forecast`.

    ``lower``/``upper`` are keyed by integer confidence level (e.g. 80, 95); ``point``
    and each band have length ``h``. ``scoreboard`` is the CV scoreboard (empty when a
    model override bypasses CV). ``notes`` records fallbacks for FP&A auditability.
    """

    model: str
    point: list[float]
    lower: dict[int, list[float]]
    upper: dict[int, list[float]]
    scoreboard: list[ModelScore]
    seasonal_period: int
    notes: list[str]


def default_candidates(
    history: ArrayLike, m: int, allow_seasonal_models: bool
) -> dict[str, CandidateFn]:
    """Build the candidate pool sized to the data (DESIGN.md 3.2 step 3).

    Always includes the explainable Tier-1 methods and baselines; adds ``seasonal_naive``
    (bound with ``m``) when seasonal models are allowed; merges in the optional
    statsforecast models when the library is available.
    """
    candidates: dict[str, CandidateFn] = {
        "naive": baselines.naive,
        "drift": baselines.drift,
        "window_average": baselines.window_average,
        "moving_average": classic.moving_average,
        "straight_line": classic.straight_line,
        "simple_linear_regression": classic.simple_linear_regression,
    }
    if allow_seasonal_models:
        candidates["seasonal_naive"] = partial(baselines.seasonal_naive, m=m)
    candidates.update(advanced_models(m))
    return candidates


def _naive_denominator(train: np.ndarray, m: int) -> float:
    """In-sample MAE of the (seasonal) naive forecast -- the MASE scaling denominator."""
    use_m = m if (m > 1 and train.size > m) else 1
    if train.size <= use_m:
        return float("nan")
    diffs = np.abs(train[use_m:] - train[:-use_m])
    denom = float(np.mean(diffs))
    if denom == 0.0 or not np.isfinite(denom):
        return float("nan")
    return denom


def _iter_windows(
    n: int, h: int, n_windows: int, step: int, m: int
) -> Iterable[int]:
    """Yield valid rolling-origin cutoffs (DESIGN.md 3.2 step 4)."""
    min_cutoff = max(2, m + 1)
    for w in range(n_windows):
        cutoff = n - h - (n_windows - 1 - w) * step
        if cutoff < min_cutoff:
            continue
        yield cutoff


def rolling_origin_cv(
    history: ArrayLike,
    candidates: dict[str, CandidateFn],
    h: int,
    n_windows: int = 3,
    step: int = 1,
    m: int = 1,
) -> list[ModelScore]:
    """Rolling-origin cross-validation (DESIGN.md 3.2 step 4 -- NOT random k-fold).

    For each window, train only on data before the cutoff, forecast ``h``, and compare to
    the held-out actuals. Errors are accumulated across windows; MASE uses the per-window
    naive (seasonal when ``m > 1`` and the train is long enough) denominator. Candidates
    that raise in a window are skipped for that window. Returns ModelScores sorted
    ascending by MASE (NaN last).
    """
    series = np.asarray(history, dtype=float).ravel()
    n = series.size

    abs_err: dict[str, list[float]] = {name: [] for name in candidates}
    sq_err: dict[str, list[float]] = {name: [] for name in candidates}
    scaled_err: dict[str, list[float]] = {name: [] for name in candidates}

    for cutoff in _iter_windows(n, h, n_windows, step, m):
        train = series[:cutoff]
        test = series[cutoff : cutoff + h]
        if test.size == 0:
            continue
        denom = _naive_denominator(train, m)
        for name, fn in candidates.items():
            try:
                pred = np.asarray(fn(train, h), dtype=float).ravel()[: test.size]
            except Exception:
                continue
            if pred.size != test.size or not np.all(np.isfinite(pred)):
                continue
            errors = test - pred
            abs_e = np.abs(errors)
            abs_err[name].extend(abs_e.tolist())
            sq_err[name].extend((errors**2).tolist())
            if np.isfinite(denom):
                scaled_err[name].extend((abs_e / denom).tolist())

    scoreboard: list[ModelScore] = []
    for name in candidates:
        if abs_err[name]:
            mae_v = float(np.mean(abs_err[name]))
            rmse_v = float(np.sqrt(np.mean(sq_err[name])))
        else:
            mae_v = float("nan")
            rmse_v = float("nan")
        mase_v = float(np.mean(scaled_err[name])) if scaled_err[name] else float("nan")
        scoreboard.append(ModelScore(model=name, mase=mase_v, rmse=rmse_v, mae=mae_v))

    scoreboard.sort(
        key=lambda s: (np.isnan(s.mase), s.mase if not np.isnan(s.mase) else 0.0)
    )
    return scoreboard


def _winner_residuals(
    history: np.ndarray,
    fn: CandidateFn,
    h: int,
    n_windows: int,
    step: int,
    m: int,
) -> list[float]:
    """Collect the winner's CV residuals (``y - yhat``) for conformal calibration."""
    residuals: list[float] = []
    n = history.size
    for cutoff in _iter_windows(n, h, n_windows, step, m):
        train = history[:cutoff]
        test = history[cutoff : cutoff + h]
        if test.size == 0:
            continue
        try:
            pred = np.asarray(fn(train, h), dtype=float).ravel()[: test.size]
        except Exception:
            continue
        if pred.size != test.size or not np.all(np.isfinite(pred)):
            continue
        residuals.extend((test - pred).tolist())
    return residuals


def auto_forecast(
    history: ArrayLike,
    h: int | None = None,
    *,
    m: int | None = None,
    freq: str = "M",
    levels: Sequence[int] = (80, 95),
    allow_seasonal: bool | None = None,
    min_cycles: int = 2,
    n_windows: int = 3,
    model_override: str | None = None,
) -> ForecastResult:
    """Autonomously select, fit, and forecast a single series (DESIGN.md 3.2).

    Args:
        history: 1-D series (array-like).
        h: forecast horizon (defaults to 12).
        m: seasonal period; inferred from ``freq`` when ``None``.
        freq: calendar frequency string used to infer ``m`` (DESIGN.md 3.2).
        levels: confidence levels for conformal intervals.
        allow_seasonal: override the short-series seasonal gate (DESIGN.md 3.4).
        min_cycles: cycles required by the seasonal gate.
        n_windows: rolling-origin CV windows.
        model_override: skip CV and force this candidate (if present in the pool).

    Returns a :class:`ForecastResult`. Never raises -- degrades to naive on short/bad
    input and records the reason in ``notes``.
    """
    series = np.asarray(history, dtype=float).ravel()
    h = h or 12
    m = m if m is not None else infer_seasonal_period(freq)
    n = series.size

    notes: list[str] = []

    allow_sn = (
        allow_seasonal
        if allow_seasonal is not None
        else allow_seasonal_fn(n, m, min_cycles)
    )
    if m > 1 and not allow_sn:
        notes.append("insufficient history for seasonal models")

    candidates = default_candidates(series, m, allow_sn)

    # Degenerate input: nothing to fit -> naive.
    if n == 0:
        notes.append("empty history -> naive")
        point = baselines.naive(series, h)
        lower, upper = conformal_intervals(point, [], levels)
        return ForecastResult(
            model="naive",
            point=[float(v) for v in point],
            lower=lower,
            upper=upper,
            scoreboard=[],
            seasonal_period=m,
            notes=notes,
        )

    scoreboard: list[ModelScore] = []
    if model_override is not None and model_override in candidates:
        selected = model_override
        notes.append(f"model override -> {selected}")
    else:
        if model_override is not None:
            notes.append(f"model override '{model_override}' not in pool -> CV select")
        scoreboard = rolling_origin_cv(
            series, candidates, h, n_windows=n_windows, step=1, m=m
        )
        chosen = next(
            (s.model for s in scoreboard if not np.isnan(s.mase)),
            None,
        )
        if chosen is None:
            selected = "naive"
            notes.append("all CV models failed -> naive")
        else:
            selected = chosen

    winner_fn = candidates.get(selected, baselines.naive)

    # Refit winner on full history.
    try:
        point = np.asarray(winner_fn(series, h), dtype=float).ravel()
        if point.size != h or not np.all(np.isfinite(point)):
            raise ValueError("winner produced invalid forecast")
    except Exception:
        notes.append(f"winner '{selected}' failed on full history -> naive")
        selected = "naive"
        winner_fn = baselines.naive
        point = baselines.naive(series, h)

    residuals = _winner_residuals(series, winner_fn, h, n_windows, step=1, m=m)
    lower, upper = conformal_intervals(point, residuals, levels)

    return ForecastResult(
        model=selected,
        point=[float(v) for v in point],
        lower=lower,
        upper=upper,
        scoreboard=scoreboard,
        seasonal_period=m,
        notes=notes,
    )
