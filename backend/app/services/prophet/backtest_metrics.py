"""Backtest metrics calculation for Prophet forecasts."""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict


def calculate_backtest_metrics(
    actual: pd.Series,
    forecast: pd.Series,
) -> Dict[str, float]:
    """
    Calculate backtest metrics comparing forecast to actual values.

    Args:
        actual: Series of actual prices (indexed by date)
        forecast: Series of forecasted prices (indexed by date)

    Returns:
        Dict with metrics: mape, rmse, mae, correlation, r_squared, direction_accuracy
    """
    # Align series on common indices
    common_idx = actual.index.intersection(forecast.index)

    if len(common_idx) == 0:
        return {
            "mape": 0.0,
            "rmse": 0.0,
            "mae": 0.0,
            "correlation": 0.0,
            "r_squared": 0.0,
            "direction_accuracy": 0.0,
            "days_forecasted": len(forecast),
            "days_with_actual": 0,
        }

    actual_aligned = actual.loc[common_idx].astype(float)
    forecast_aligned = forecast.loc[common_idx].astype(float)

    # Remove NaN values
    mask = ~(actual_aligned.isna() | forecast_aligned.isna())
    actual_clean = actual_aligned[mask]
    forecast_clean = forecast_aligned[mask]

    if len(actual_clean) < 2:
        return {
            "mape": 0.0,
            "rmse": 0.0,
            "mae": 0.0,
            "correlation": 0.0,
            "r_squared": 0.0,
            "direction_accuracy": 0.0,
            "days_forecasted": len(forecast),
            "days_with_actual": len(actual_clean),
        }

    # Calculate errors
    errors = actual_clean - forecast_clean

    # MAE - Mean Absolute Error
    mae = float(np.mean(np.abs(errors)))

    # RMSE - Root Mean Square Error
    rmse = float(np.sqrt(np.mean(errors ** 2)))

    # MAPE - Mean Absolute Percentage Error
    # Avoid division by zero
    non_zero_mask = actual_clean != 0
    if non_zero_mask.sum() > 0:
        mape = float(np.mean(np.abs(errors[non_zero_mask] / actual_clean[non_zero_mask])) * 100)
    else:
        mape = 0.0

    # Pearson correlation
    if len(actual_clean) >= 2:
        correlation, _ = stats.pearsonr(actual_clean.values, forecast_clean.values)
        correlation = float(correlation) if not np.isnan(correlation) else 0.0
    else:
        correlation = 0.0

    # R-squared (coefficient of determination)
    r_squared = correlation ** 2

    # Direction accuracy - percentage of correct direction predictions
    if len(actual_clean) >= 2:
        actual_returns = actual_clean.pct_change().dropna()
        forecast_returns = forecast_clean.pct_change().dropna()

        # Align returns
        common_return_idx = actual_returns.index.intersection(forecast_returns.index)
        if len(common_return_idx) > 0:
            actual_dir = actual_returns.loc[common_return_idx] > 0
            forecast_dir = forecast_returns.loc[common_return_idx] > 0
            direction_accuracy = float((actual_dir == forecast_dir).mean() * 100)
        else:
            direction_accuracy = 0.0
    else:
        direction_accuracy = 0.0

    return {
        "mape": round(mape, 4),
        "rmse": round(rmse, 4),
        "mae": round(mae, 4),
        "correlation": round(correlation, 4),
        "r_squared": round(r_squared, 4),
        "direction_accuracy": round(direction_accuracy, 2),
        "days_forecasted": len(forecast),
        "days_with_actual": len(actual_clean),
    }
