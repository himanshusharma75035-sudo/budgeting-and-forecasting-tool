"""Deterministic unit tests for the forecasting engine (DESIGN.md section 3).

numpy-only: statsforecast/statsmodels are NOT required. All expected values are computed
by hand and encoded as exact constants or pytest.approx.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.domain.forecasting import baselines, classic, metrics
from app.domain.forecasting.auto_select import auto_forecast


# --------------------------------------------------------------------------- metrics
def test_mae_exact():
    y_true = np.array([10.0, 12.0, 14.0])
    y_pred = np.array([11.0, 11.0, 15.0])
    # |errors| = 1, 1, 1 -> mean 1.0
    assert metrics.mae(y_true, y_pred) == pytest.approx(1.0)


def test_rmse_exact():
    y_true = np.array([10.0, 12.0, 14.0])
    y_pred = np.array([11.0, 11.0, 15.0])
    # errors squared = 1, 1, 1 -> sqrt(mean) = 1.0
    assert metrics.rmse(y_true, y_pred) == pytest.approx(1.0)


def test_mase_exact():
    # naive diffs of [2,4,6,8] are all 2 -> denom 2; mae([10],[11]) = 1 -> 1/2 = 0.5
    y_train = np.array([2.0, 4.0, 6.0, 8.0])
    result = metrics.mase(np.array([10.0]), np.array([11.0]), y_train, m=1)
    assert result == pytest.approx(0.5)


def test_mape_skips_zero_actuals():
    y_true = np.array([0.0, 100.0])
    y_pred = np.array([5.0, 110.0])
    # only the second position counts: 100*|10/100| = 10.0
    assert metrics.mape(y_true, y_pred) == pytest.approx(10.0)


def test_mape_all_zero_is_nan():
    assert np.isnan(metrics.mape(np.array([0.0, 0.0]), np.array([1.0, 2.0])))


def test_smape_handles_zero_over_zero():
    # both zero -> 0 contribution; (100,110): 200*10/210
    y_true = np.array([0.0, 100.0])
    y_pred = np.array([0.0, 110.0])
    expected = (0.0 + 200.0 * 10.0 / 210.0) / 2.0
    assert metrics.smape(y_true, y_pred) == pytest.approx(expected)


def test_mase_flat_train_is_nan():
    # flat training -> denom 0 -> nan
    result = metrics.mase(
        np.array([1.0]), np.array([2.0]), np.array([5.0, 5.0, 5.0]), m=1
    )
    assert np.isnan(result)


# --------------------------------------------------------------------------- baselines
def test_naive_repeats_last():
    assert baselines.naive([1, 2, 3], 2).tolist() == [3.0, 3.0]


def test_seasonal_naive_tiles_last_m():
    # last m=2 of [1,2,3,4] is [3,4]; horizon 2 -> [3,4]
    assert baselines.seasonal_naive([1, 2, 3, 4], 2, 2).tolist() == [3.0, 4.0]


def test_seasonal_naive_tiles_beyond_one_cycle():
    # last m=2 is [3,4]; horizon 4 -> [3,4,3,4]
    assert baselines.seasonal_naive([1, 2, 3, 4], 4, 2).tolist() == [3.0, 4.0, 3.0, 4.0]


def test_drift_linear():
    # slope = (4-2)/(2-1) = 2; k=1,2,3 -> 6,8,10
    assert baselines.drift([2, 4], 3).tolist() == [6.0, 8.0, 10.0]


def test_window_average_flat():
    assert baselines.window_average([1, 2, 3, 9], 2, window=3).tolist() == pytest.approx(
        [(2 + 3 + 9) / 3, (2 + 3 + 9) / 3]
    )


# --------------------------------------------------------------------------- classic
def test_simple_linear_regression_perfect_line():
    # y = x + 1 on indices 0..4; extrapolate indices 5,6,7 -> 6,7,8
    pred = classic.simple_linear_regression([1, 2, 3, 4, 5], 3)
    assert pred.tolist() == pytest.approx([6.0, 7.0, 8.0])


def test_straight_line_growth_rate():
    # g = (110-100)/100 = 0.1; 110*1.1 = 121, 110*1.21 = 133.1
    pred = classic.straight_line([100, 110], 2)
    assert pred.tolist() == pytest.approx([121.0, 133.1])


def test_straight_line_zero_prev_falls_back_to_naive():
    # prev == 0 -> naive (repeat last)
    pred = classic.straight_line([0, 50], 3)
    assert pred.tolist() == [50.0, 50.0, 50.0]


def test_moving_average_flat():
    pred = classic.moving_average([10, 20, 30], 2, window=2)
    assert pred.tolist() == pytest.approx([25.0, 25.0])


def test_multiple_linear_regression_recovers_plane():
    # y = 1 + 2*x1 + 3*x2 exactly
    X = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [2.0, 1.0]])
    y = 1.0 + 2.0 * X[:, 0] + 3.0 * X[:, 1]
    X_future = np.array([[3.0, 2.0], [4.0, 0.0]])
    pred = classic.multiple_linear_regression(y, X, X_future)
    assert pred.tolist() == pytest.approx([1 + 2 * 3 + 3 * 2, 1 + 2 * 4 + 3 * 0])


# --------------------------------------------------------------------------- auto_forecast
def _deterministic_series(n: int = 36) -> np.ndarray:
    # linear trend + fixed annual seasonality, no randomness
    t = np.arange(n, dtype=float)
    return 100.0 + 2.0 * t + 10.0 * np.sin(2.0 * np.pi * t / 12.0)


def test_auto_forecast_shapes_and_levels():
    series = _deterministic_series(36)
    result = auto_forecast(series, h=6, freq="M", levels=(80, 95))
    assert len(result.point) == 6
    assert set(result.lower.keys()) == {80, 95}
    assert set(result.upper.keys()) == {80, 95}
    assert len(result.lower[80]) == 6
    assert len(result.upper[95]) == 6
    assert isinstance(result.model, str) and result.model
    assert result.seasonal_period == 12


def test_auto_forecast_scoreboard_sorted_mase_ascending_nan_last():
    series = _deterministic_series(36)
    result = auto_forecast(series, h=6, freq="M")
    mases = [s.mase for s in result.scoreboard]
    finite = [v for v in mases if not np.isnan(v)]
    # finite scores are non-decreasing
    assert finite == sorted(finite)
    # all NaNs sit at the tail
    seen_nan = False
    for v in mases:
        if np.isnan(v):
            seen_nan = True
        elif seen_nan:
            pytest.fail("finite MASE appeared after a NaN MASE")


def test_auto_forecast_nested_intervals():
    series = _deterministic_series(36)
    result = auto_forecast(series, h=6, freq="M", levels=(80, 95))
    for i in range(6):
        assert result.lower[95][i] <= result.lower[80][i]
        assert result.upper[95][i] >= result.upper[80][i]


def test_auto_forecast_model_override_naive():
    series = _deterministic_series(36)
    result = auto_forecast(series, h=4, freq="M", model_override="naive")
    last = float(series[-1])
    assert result.model == "naive"
    assert result.point == pytest.approx([last, last, last, last])


def test_auto_forecast_short_series_no_exception():
    # length 5 -- well below 2 seasonal cycles; must degrade gracefully, never raise
    result = auto_forecast(np.array([1.0, 2.0, 3.0, 4.0, 5.0]), h=3, freq="M")
    assert len(result.point) == 3
    assert all(np.isfinite(result.point))
    assert isinstance(result.model, str) and result.model
