"""XGBoost residual correction model for Prophet hybrid forecasting.

Workflow:
1. Prophet forecast → ŷ_prophet
2. Residuals = actual - ŷ_prophet
3. XGBoost learns residual patterns
4. Hybrid = ŷ_prophet + XGBoost.predict(features)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import logging

import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from .config import XGBoostConfig
from .feature_engine import XGBoostFeatureEngine

logger = logging.getLogger(__name__)


@dataclass
class XGBoostMetrics:
    """Metrics comparing Prophet-only vs Hybrid forecasts."""

    # Prophet-only metrics
    prophet_mae: float
    prophet_rmse: float
    prophet_mape: float
    prophet_r2: float

    # Hybrid metrics
    hybrid_mae: float
    hybrid_rmse: float
    hybrid_mape: float
    hybrid_r2: float

    # Improvement percentages
    mae_improvement_pct: float
    rmse_improvement_pct: float
    mape_improvement_pct: float
    r2_improvement_pct: float


@dataclass
class FeatureImportance:
    """Feature importance information."""

    feature_name: str
    importance: float
    rank: int


@dataclass
class HybridForecastResult:
    """Result of hybrid Prophet + XGBoost forecast."""

    # Forecast data
    dates: List[str]
    prophet_predictions: List[float]
    hybrid_predictions: List[float]
    lower_bound: List[float]
    upper_bound: List[float]

    # Metadata
    training_end_date: str
    forecast_start_date: str

    # Metrics (for in-sample validation)
    metrics: Optional[XGBoostMetrics] = None

    # Feature importance
    feature_importance: List[FeatureImportance] = field(default_factory=list)


class XGBoostResidualCorrector:
    """
    XGBoost model for correcting Prophet forecast residuals.

    Creates a hybrid forecast by:
    1. Training on residuals = actual - prophet_prediction
    2. Learning patterns from 27 engineered features
    3. Adding predicted residuals back to Prophet forecast
    """

    def __init__(self, config: Optional[XGBoostConfig] = None):
        """Initialize corrector with configuration."""
        self.config = config or XGBoostConfig()
        self.feature_engine = XGBoostFeatureEngine(self.config)
        self.model: Optional[xgb.XGBRegressor] = None
        self.feature_names: List[str] = []
        self._is_trained = False

    def fit(
        self,
        df: pd.DataFrame,
        prophet_forecast: pd.DataFrame,
        actual_values: pd.Series
    ) -> XGBoostMetrics:
        """
        Train XGBoost on Prophet residuals.

        Args:
            df: OHLCV DataFrame with columns [timestamp, open, high, low, close, volume]
            prophet_forecast: Prophet forecast DataFrame with yhat, trend, etc.
            actual_values: Actual price values (y)

        Returns:
            XGBoostMetrics comparing Prophet-only vs Hybrid performance
        """
        logger.info("Training XGBoost residual corrector...")

        # Calculate residuals: actual - prophet_predicted
        prophet_predictions = prophet_forecast["yhat"].values[:len(actual_values)]
        residuals = pd.Series(actual_values.values - prophet_predictions)

        # Generate features
        features, self.feature_names = self.feature_engine.generate_features(
            df, prophet_forecast, residuals
        )

        # Prepare for training (drop NaN rows)
        X, y = self.feature_engine.prepare_for_training(features, self.feature_names)

        # Time-based split (NO random shuffle - critical for time series!)
        split_idx = int(len(X) * self.config.train_test_split)
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

        logger.info(
            f"Training on {len(X_train)} samples, validating on {len(X_test)} samples"
        )

        # Create and train XGBoost model
        self.model = xgb.XGBRegressor(
            n_estimators=self.config.n_estimators,
            max_depth=self.config.max_depth,
            learning_rate=self.config.learning_rate,
            subsample=self.config.subsample,
            colsample_bytree=self.config.colsample_bytree,
            min_child_weight=self.config.min_child_weight,
            reg_alpha=self.config.reg_alpha,
            reg_lambda=self.config.reg_lambda,
            random_state=self.config.random_state,
            n_jobs=-1,
            verbosity=0,
        )

        # Fit with early stopping
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False,
        )

        self._is_trained = True

        # Calculate metrics on test set
        metrics = self._calculate_metrics(
            X_test,
            y_test,
            prophet_predictions[split_idx + self.config.min_warmup_rows:split_idx + self.config.min_warmup_rows + len(X_test)],
            actual_values.values[split_idx + self.config.min_warmup_rows:split_idx + self.config.min_warmup_rows + len(X_test)]
        )

        logger.info(
            f"Training complete. MAE improvement: {metrics.mae_improvement_pct:.1f}%"
        )

        return metrics

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict residual corrections.

        Args:
            X: Feature DataFrame

        Returns:
            Array of predicted residuals
        """
        if not self._is_trained or self.model is None:
            raise ValueError("Model must be trained before prediction")

        return self.model.predict(X)

    def predict_hybrid(
        self,
        df: pd.DataFrame,
        prophet_forecast: pd.DataFrame,
        actual_values: Optional[pd.Series] = None
    ) -> HybridForecastResult:
        """
        Generate hybrid Prophet + XGBoost predictions for the ENTIRE forecast period.

        This includes both:
        1. Historical data (where OHLCV exists) - full feature set
        2. Future data (forecast period) - only Time + Prophet features

        Args:
            df: OHLCV DataFrame (historical data)
            prophet_forecast: Prophet forecast DataFrame (historical + future)
            actual_values: Actual values (for metrics, optional)

        Returns:
            HybridForecastResult with predictions for entire period
        """
        if not self._is_trained:
            raise ValueError("Model must be trained before prediction")

        # Get Prophet predictions for entire period
        prophet_preds = prophet_forecast["yhat"].values
        n_historical = len(df)
        n_total = len(prophet_forecast)
        n_future = n_total - n_historical

        logger.info(
            f"Generating hybrid predictions: {n_historical} historical + {n_future} future = {n_total} total"
        )

        # === Part 1: Historical predictions (full feature set) ===
        if actual_values is not None:
            residuals = pd.Series(
                actual_values.values[:min(len(actual_values), n_historical)] -
                prophet_preds[:min(len(actual_values), n_historical)]
            )
        else:
            residuals = pd.Series(np.zeros(n_historical))

        # Generate features for historical data
        historical_features, _ = self.feature_engine.generate_features(
            df, prophet_forecast.iloc[:n_historical], residuals
        )

        # Prepare features (fill NaN for prediction)
        X_historical = historical_features[self.feature_names].ffill().fillna(0)

        # Predict residual corrections for historical period
        historical_corrections = self.predict(X_historical)

        # === Part 2: Future predictions (Time + Prophet features only) ===
        if n_future > 0:
            # Generate features for future dates
            future_features = self.feature_engine.generate_future_features(
                prophet_forecast.iloc[n_historical:],
                self.feature_names
            )

            # For features not available in future, use zeros or last known value
            X_future = pd.DataFrame(index=range(n_future), columns=self.feature_names)

            for col in self.feature_names:
                if col in future_features.columns:
                    X_future[col] = future_features[col].values
                else:
                    # Use the last historical value for unavailable features
                    X_future[col] = X_historical[col].iloc[-1] if col in X_historical.columns else 0

            X_future = X_future.astype(float).fillna(0)

            # Predict residual corrections for future period
            future_corrections = self.predict(X_future)
        else:
            future_corrections = np.array([])

        # === Combine historical and future ===
        all_corrections = np.concatenate([historical_corrections, future_corrections])

        # Hybrid predictions = Prophet + XGBoost residual correction
        hybrid_preds = prophet_preds[:len(all_corrections)] + all_corrections

        # Get confidence bounds from Prophet and adjust
        lower_bound = prophet_forecast["yhat_lower"].values[:len(all_corrections)] + all_corrections
        upper_bound = prophet_forecast["yhat_upper"].values[:len(all_corrections)] + all_corrections

        # Calculate metrics on historical data only (where we have actual values)
        metrics = None
        if actual_values is not None and len(actual_values) > 0:
            n_eval = min(len(actual_values), len(historical_corrections))
            actual_subset = actual_values.values[:n_eval]
            metrics = self._calculate_metrics_direct(
                prophet_preds[:n_eval],
                hybrid_preds[:n_eval],
                actual_subset
            )

        # Get feature importance
        feature_importance = self.get_feature_importance(top_n=10)

        # Extract dates for entire period
        if "ds" in prophet_forecast.columns:
            ds_col = prophet_forecast["ds"].iloc[:len(all_corrections)]
            if hasattr(ds_col, 'dt'):
                dates = ds_col.dt.strftime("%Y-%m-%d").tolist()
            else:
                dates = pd.to_datetime(ds_col).dt.strftime("%Y-%m-%d").tolist()
        else:
            # Fallback: use df timestamps + extrapolate
            dates = df["timestamp"].astype(str).str[:10].tolist()

        # Determine training end date (last historical date)
        training_end_date = str(df["timestamp"].iloc[-1])[:10]
        # Forecast starts after last historical date
        if n_future > 0 and "ds" in prophet_forecast.columns:
            forecast_start_date = pd.to_datetime(prophet_forecast["ds"].iloc[n_historical]).strftime("%Y-%m-%d")
        else:
            forecast_start_date = training_end_date

        logger.info(
            f"Hybrid prediction complete: {len(dates)} dates, "
            f"training_end={training_end_date}, forecast_start={forecast_start_date}"
        )

        return HybridForecastResult(
            dates=dates,
            prophet_predictions=prophet_preds[:len(all_corrections)].tolist(),
            hybrid_predictions=hybrid_preds.tolist(),
            lower_bound=lower_bound.tolist(),
            upper_bound=upper_bound.tolist(),
            training_end_date=training_end_date,
            forecast_start_date=forecast_start_date,
            metrics=metrics,
            feature_importance=feature_importance,
        )

    def get_feature_importance(self, top_n: int = 10) -> List[FeatureImportance]:
        """
        Get top N most important features.

        Args:
            top_n: Number of top features to return

        Returns:
            List of FeatureImportance objects
        """
        if not self._is_trained or self.model is None:
            return []

        importances = self.model.feature_importances_
        indices = np.argsort(importances)[::-1]

        result = []
        for rank, idx in enumerate(indices[:top_n], start=1):
            result.append(FeatureImportance(
                feature_name=self.feature_names[idx],
                importance=float(importances[idx]),
                rank=rank,
            ))

        return result

    def _calculate_metrics(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        prophet_preds: np.ndarray,
        actual: np.ndarray
    ) -> XGBoostMetrics:
        """Calculate comparison metrics between Prophet and Hybrid."""
        # Predict residual corrections
        residual_corrections = self.predict(X_test)

        # Ensure arrays are same length
        min_len = min(len(prophet_preds), len(actual), len(residual_corrections))
        prophet_preds = prophet_preds[:min_len]
        actual = actual[:min_len]
        residual_corrections = residual_corrections[:min_len]

        # Hybrid predictions
        hybrid_preds = prophet_preds + residual_corrections

        return self._calculate_metrics_direct(prophet_preds, hybrid_preds, actual)

    def _calculate_metrics_direct(
        self,
        prophet_preds: np.ndarray,
        hybrid_preds: np.ndarray,
        actual: np.ndarray
    ) -> XGBoostMetrics:
        """Calculate metrics from direct predictions."""
        # Prophet-only metrics
        prophet_mae = mean_absolute_error(actual, prophet_preds)
        prophet_rmse = np.sqrt(mean_squared_error(actual, prophet_preds))
        prophet_mape = self._calculate_mape(actual, prophet_preds)
        prophet_r2 = r2_score(actual, prophet_preds)

        # Hybrid metrics
        hybrid_mae = mean_absolute_error(actual, hybrid_preds)
        hybrid_rmse = np.sqrt(mean_squared_error(actual, hybrid_preds))
        hybrid_mape = self._calculate_mape(actual, hybrid_preds)
        hybrid_r2 = r2_score(actual, hybrid_preds)

        # Calculate improvements (positive = hybrid is better)
        mae_improvement = (prophet_mae - hybrid_mae) / prophet_mae * 100 if prophet_mae > 0 else 0
        rmse_improvement = (prophet_rmse - hybrid_rmse) / prophet_rmse * 100 if prophet_rmse > 0 else 0
        mape_improvement = (prophet_mape - hybrid_mape) / prophet_mape * 100 if prophet_mape > 0 else 0
        r2_improvement = (hybrid_r2 - prophet_r2) / abs(prophet_r2) * 100 if prophet_r2 != 0 else 0

        return XGBoostMetrics(
            prophet_mae=prophet_mae,
            prophet_rmse=prophet_rmse,
            prophet_mape=prophet_mape,
            prophet_r2=prophet_r2,
            hybrid_mae=hybrid_mae,
            hybrid_rmse=hybrid_rmse,
            hybrid_mape=hybrid_mape,
            hybrid_r2=hybrid_r2,
            mae_improvement_pct=mae_improvement,
            rmse_improvement_pct=rmse_improvement,
            mape_improvement_pct=mape_improvement,
            r2_improvement_pct=r2_improvement,
        )

    def _calculate_mape(self, actual: np.ndarray, predicted: np.ndarray) -> float:
        """Calculate Mean Absolute Percentage Error."""
        mask = actual != 0
        if not np.any(mask):
            return 0.0
        return float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100)

    @property
    def is_trained(self) -> bool:
        """Check if model is trained."""
        return self._is_trained
