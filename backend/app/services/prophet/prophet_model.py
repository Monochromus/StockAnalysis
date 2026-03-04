"""Core Prophet forecasting model."""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import logging

from prophet import Prophet

from .config import ProphetConfig, ForecastHorizon
from .indicators import ProphetIndicators

logger = logging.getLogger(__name__)


@dataclass
class ForecastResult:
    """Result of a single forecast."""

    horizon: str  # "long_term", "mid_term", "short_term"
    forecast_df: pd.DataFrame  # Prophet forecast DataFrame
    model: Prophet  # Trained Prophet model
    training_end_date: str  # Last date of training data
    forecast_start_date: str  # First forecast date
    mape: Optional[float] = None  # Mean Absolute Percentage Error
    rmse: Optional[float] = None  # Root Mean Square Error


@dataclass
class ComponentData:
    """Seasonal component data for visualization."""

    trend: List[Dict[str, Any]]
    weekly: Optional[List[Dict[str, Any]]] = None
    monthly: Optional[List[Dict[str, Any]]] = None
    yearly: Optional[List[Dict[str, Any]]] = None


class ProphetForecaster:
    """
    Prophet-based forecaster for price, volatility, and RSI predictions.

    Supports multiple forecast horizons using different training data fractions.
    """

    def __init__(self, config: Optional[ProphetConfig] = None):
        """
        Initialize forecaster.

        Args:
            config: Prophet configuration, uses defaults if not provided
        """
        self.config = config or ProphetConfig()
        self.horizons = ForecastHorizon.get_defaults()

        # Store trained models and results
        self._price_forecasts: Dict[str, ForecastResult] = {}
        self._volatility_forecasts: Dict[str, ForecastResult] = {}
        self._rsi_forecasts: Dict[str, ForecastResult] = {}

        # Store raw data for component extraction
        self._price_models: Dict[str, Prophet] = {}

    def _create_prophet_model(self, suppress_output: bool = True) -> Prophet:
        """Create a configured Prophet model instance."""
        model = Prophet(
            yearly_seasonality=self.config.yearly_seasonality,
            weekly_seasonality=self.config.weekly_seasonality,
            daily_seasonality=self.config.daily_seasonality,
            changepoint_prior_scale=self.config.changepoint_prior_scale,
            seasonality_prior_scale=self.config.seasonality_prior_scale,
            changepoint_range=self.config.changepoint_range,
            interval_width=self.config.interval_width,
            growth=self.config.growth,
        )

        # Note: Custom monthly seasonality removed - it was causing extreme oscillations
        # in stock price forecasts. Stock prices don't have true seasonal patterns.

        # Suppress Stan output
        if suppress_output:
            import cmdstanpy
            cmdstanpy.utils.get_logger().setLevel(logging.WARNING)

        return model

    def _prepare_data_for_horizon(
        self,
        df: pd.DataFrame,
        horizon: ForecastHorizon
    ) -> pd.DataFrame:
        """
        Prepare training data for a specific horizon.

        Uses only the specified fraction of historical data.
        """
        n_rows = len(df)
        start_idx = int(n_rows * (1 - horizon.data_fraction))
        return df.iloc[start_idx:].reset_index(drop=True)

    def _calculate_metrics(
        self,
        actual: pd.Series,
        predicted: pd.Series
    ) -> Tuple[float, float]:
        """Calculate MAPE and RMSE."""
        # Filter out zeros and NaN for MAPE
        mask = (actual != 0) & (~actual.isna()) & (~predicted.isna())

        if mask.sum() == 0:
            return 0.0, 0.0

        actual_clean = actual[mask]
        predicted_clean = predicted[mask]

        # MAPE
        mape = np.mean(np.abs((actual_clean - predicted_clean) / actual_clean)) * 100

        # RMSE
        rmse = np.sqrt(np.mean((actual_clean - predicted_clean) ** 2))

        return float(mape), float(rmse)

    def _fit_and_forecast(
        self,
        df: pd.DataFrame,
        horizon: ForecastHorizon,
        periods: int,
        freq: str = "D"
    ) -> ForecastResult:
        """
        Fit Prophet model and generate forecast.

        Args:
            df: DataFrame with 'ds' and 'y' columns
            horizon: Forecast horizon configuration
            periods: Number of periods to forecast
            freq: Frequency ('D' for daily)

        Returns:
            ForecastResult with forecast data and model
        """
        # Prepare training data
        train_df = self._prepare_data_for_horizon(df, horizon)

        # Create and fit model
        model = self._create_prophet_model()

        # Handle cap/floor for logistic growth
        if self.config.growth == "logistic":
            if self.config.cap is not None:
                train_df["cap"] = self.config.cap
            if self.config.floor is not None:
                train_df["floor"] = self.config.floor

        model.fit(train_df)

        # Create future dataframe
        future = model.make_future_dataframe(periods=periods, freq=freq)

        if self.config.growth == "logistic":
            if self.config.cap is not None:
                future["cap"] = self.config.cap
            if self.config.floor is not None:
                future["floor"] = self.config.floor

        # Generate forecast
        forecast = model.predict(future)

        # Calculate in-sample metrics
        historical_forecast = forecast[forecast["ds"].isin(train_df["ds"])]
        merged = train_df.merge(
            historical_forecast[["ds", "yhat"]],
            on="ds",
            how="inner"
        )

        mape, rmse = self._calculate_metrics(merged["y"], merged["yhat"])

        # Get date boundaries
        training_end_date = train_df["ds"].max().strftime("%Y-%m-%d")
        forecast_start_date = (
            train_df["ds"].max() + pd.Timedelta(days=1)
        ).strftime("%Y-%m-%d")

        return ForecastResult(
            horizon=horizon.name,
            forecast_df=forecast,
            model=model,
            training_end_date=training_end_date,
            forecast_start_date=forecast_start_date,
            mape=mape,
            rmse=rmse,
        )

    def forecast_price(
        self,
        df: pd.DataFrame,
        periods: int = 365
    ) -> Dict[str, ForecastResult]:
        """
        Forecast prices for all horizons.

        Args:
            df: OHLCV DataFrame with datetime index
            periods: Number of days to forecast

        Returns:
            Dict mapping horizon names to ForecastResults
        """
        # Prepare price data
        indicators = ProphetIndicators(df)
        price_df = indicators.prepare_price_data()

        results = {}

        for horizon in self.horizons:
            logger.info(f"Forecasting price for horizon: {horizon.name}")
            result = self._fit_and_forecast(price_df, horizon, periods)
            results[horizon.name] = result
            self._price_models[horizon.name] = result.model

        self._price_forecasts = results
        return results

    def forecast_indicators(
        self,
        df: pd.DataFrame,
        periods: int = 365
    ) -> Dict[str, Dict[str, ForecastResult]]:
        """
        Forecast volatility and RSI for all horizons.

        Args:
            df: OHLCV DataFrame with datetime index
            periods: Number of days to forecast

        Returns:
            Dict with 'volatility' and 'rsi' keys, each containing
            horizon name to ForecastResult mappings
        """
        indicators = ProphetIndicators(df)
        volatility_df = indicators.calculate_volatility()
        rsi_df = indicators.calculate_rsi()

        volatility_results = {}
        rsi_results = {}

        for horizon in self.horizons:
            logger.info(f"Forecasting indicators for horizon: {horizon.name}")

            # Volatility forecast
            vol_result = self._fit_and_forecast(volatility_df, horizon, periods)
            volatility_results[horizon.name] = vol_result

            # RSI forecast - need to constrain to 0-100 range
            rsi_result = self._fit_and_forecast(rsi_df, horizon, periods)
            # Clip RSI to valid range
            rsi_result.forecast_df["yhat"] = rsi_result.forecast_df["yhat"].clip(0, 100)
            rsi_result.forecast_df["yhat_lower"] = rsi_result.forecast_df["yhat_lower"].clip(0, 100)
            rsi_result.forecast_df["yhat_upper"] = rsi_result.forecast_df["yhat_upper"].clip(0, 100)
            rsi_results[horizon.name] = rsi_result

        self._volatility_forecasts = volatility_results
        self._rsi_forecasts = rsi_results

        return {
            "volatility": volatility_results,
            "rsi": rsi_results,
        }

    def forecast_all_horizons(
        self,
        df: pd.DataFrame,
        periods: int = 365
    ) -> Dict[str, Any]:
        """
        Forecast price, volatility, and RSI for all horizons.

        Args:
            df: OHLCV DataFrame with datetime index
            periods: Number of days to forecast

        Returns:
            Dict with all forecasts organized by type and horizon
        """
        price_forecasts = self.forecast_price(df, periods)
        indicator_forecasts = self.forecast_indicators(df, periods)

        return {
            "price": price_forecasts,
            "volatility": indicator_forecasts["volatility"],
            "rsi": indicator_forecasts["rsi"],
        }

    def get_components(self, horizon: str = "long_term") -> Optional[ComponentData]:
        """
        Extract seasonal components from a trained model.

        Args:
            horizon: Which horizon's model to use

        Returns:
            ComponentData with trend and seasonal components
        """
        if horizon not in self._price_models:
            logger.warning(f"No model found for horizon: {horizon}")
            return None

        model = self._price_models[horizon]
        forecast = self._price_forecasts[horizon].forecast_df

        # Extract trend
        trend_data = [
            {"ds": row["ds"].strftime("%Y-%m-%d"), "value": float(row["trend"])}
            for _, row in forecast.iterrows()
        ]

        # Extract weekly seasonality
        weekly_data = None
        if "weekly" in forecast.columns:
            weekly_data = [
                {"ds": row["ds"].strftime("%Y-%m-%d"), "value": float(row["weekly"])}
                for _, row in forecast.iterrows()
            ]

        # Extract monthly seasonality
        monthly_data = None
        if "monthly" in forecast.columns:
            monthly_data = [
                {"ds": row["ds"].strftime("%Y-%m-%d"), "value": float(row["monthly"])}
                for _, row in forecast.iterrows()
            ]

        # Extract yearly seasonality
        yearly_data = None
        if "yearly" in forecast.columns:
            yearly_data = [
                {"ds": row["ds"].strftime("%Y-%m-%d"), "value": float(row["yearly"])}
                for _, row in forecast.iterrows()
            ]

        return ComponentData(
            trend=trend_data,
            weekly=weekly_data,
            monthly=monthly_data,
            yearly=yearly_data,
        )

    def combine_forecasts(
        self,
        forecasts: Dict[str, ForecastResult],
        weights: Optional[Dict[str, float]] = None
    ) -> ForecastResult:
        """
        Combine multiple horizon forecasts into a single weighted forecast.

        Effects that appear consistently across all horizons get more weight,
        while effects that only appear in short-term get diluted.

        Weights are based on years of training data:
        - long_term: 5 years → weight 5
        - mid_term: 2 years → weight 2
        - short_term: 0.5 years → weight 0.5

        Args:
            forecasts: Dict mapping horizon names to ForecastResults
            weights: Optional custom weights, defaults to data-based weights

        Returns:
            Combined ForecastResult with weighted average predictions
        """
        # Default weights based on years of training data
        if weights is None:
            weights = {
                "long_term": 5.0,    # 5 years of data
                "mid_term": 2.0,     # 2 years of data
                "short_term": 0.5,   # 6 months of data
            }

        # Get all forecast DataFrames
        dfs = {}
        for horizon_name, result in forecasts.items():
            if horizon_name in weights:
                df = result.forecast_df.copy()
                df["_horizon"] = horizon_name
                dfs[horizon_name] = df

        if not dfs:
            raise ValueError("No valid forecasts to combine")

        # Start with long_term as base (has most dates)
        base_df = dfs.get("long_term", list(dfs.values())[0]).copy()
        combined = base_df[["ds"]].copy()

        # Columns to combine with weighted average
        value_cols = ["yhat", "yhat_lower", "yhat_upper", "trend"]

        # Add seasonal columns if they exist
        for col in ["yearly", "weekly", "monthly"]:
            if col in base_df.columns:
                value_cols.append(col)

        for col in value_cols:
            if col not in base_df.columns:
                continue

            # Initialize weighted sum and weight sum
            combined[f"{col}_weighted_sum"] = 0.0
            combined[f"{col}_weight_sum"] = 0.0

            for horizon_name, df in dfs.items():
                if col not in df.columns:
                    continue

                w = weights.get(horizon_name, 1.0)

                # Merge by date
                horizon_vals = df[["ds", col]].copy()
                horizon_vals = horizon_vals.rename(columns={col: f"{col}_{horizon_name}"})

                combined = combined.merge(horizon_vals, on="ds", how="left")

                # Add to weighted sum where values exist
                mask = combined[f"{col}_{horizon_name}"].notna()
                combined.loc[mask, f"{col}_weighted_sum"] += (
                    combined.loc[mask, f"{col}_{horizon_name}"] * w
                )
                combined.loc[mask, f"{col}_weight_sum"] += w

                # Drop temporary column
                combined = combined.drop(columns=[f"{col}_{horizon_name}"])

            # Calculate weighted average
            combined[col] = combined[f"{col}_weighted_sum"] / combined[f"{col}_weight_sum"]
            combined = combined.drop(columns=[f"{col}_weighted_sum", f"{col}_weight_sum"])

        # Ensure ds column is datetime type (required for XGBoost date extraction)
        if not pd.api.types.is_datetime64_any_dtype(combined["ds"]):
            combined["ds"] = pd.to_datetime(combined["ds"])

        # Drop rows with NaN in yhat (can happen if horizons don't overlap fully)
        combined = combined.dropna(subset=["yhat"])

        # Use long_term dates for metadata
        long_term = forecasts.get("long_term", list(forecasts.values())[0])

        logger.info(
            f"Combined {len(forecasts)} horizon forecasts with weights: {weights}, "
            f"result has {len(combined)} rows"
        )

        return ForecastResult(
            horizon="combined",
            forecast_df=combined,
            model=long_term.model,  # Use long_term model for components
            training_end_date=long_term.training_end_date,
            forecast_start_date=long_term.forecast_start_date,
            mape=long_term.mape,  # Could calculate combined MAPE
            rmse=long_term.rmse,
        )

    def backtest_forecast(
        self,
        df: pd.DataFrame,
        cutoff_date: str,
        periods: int = 365
    ) -> Tuple[ForecastResult, pd.DataFrame]:
        """
        Backtest: Train Prophet ONLY on data BEFORE cutoff_date.

        CRITICAL: Strict data isolation - NO data leak!
        The model must not see any data on or after the cutoff date.

        Args:
            df: OHLCV DataFrame with datetime index
            cutoff_date: String date (YYYY-MM-DD) - training ends BEFORE this date
            periods: Number of days to forecast from cutoff

        Returns:
            Tuple of (ForecastResult, full_df) where full_df includes actual data
            for comparison
        """
        cutoff = pd.to_datetime(cutoff_date)

        # STRICT: Only data BEFORE cutoff (not <=)
        train_data = df[df.index < cutoff].copy()

        if len(train_data) < 30:
            raise ValueError(
                f"Insufficient training data before {cutoff_date}. "
                f"Need at least 30 data points, got {len(train_data)}."
            )

        logger.info(
            f"Backtest training: {len(train_data)} days before {cutoff_date}, "
            f"forecasting {periods} days"
        )

        # Prepare price data for Prophet
        indicators = ProphetIndicators(train_data)
        price_df = indicators.prepare_price_data()

        # Create and fit Prophet model
        model = self._create_prophet_model()

        # Handle cap/floor for logistic growth
        if self.config.growth == "logistic":
            if self.config.cap is not None:
                price_df["cap"] = self.config.cap
            if self.config.floor is not None:
                price_df["floor"] = self.config.floor

        model.fit(price_df)

        # Create future dataframe starting from cutoff
        future = model.make_future_dataframe(periods=periods, freq="D")

        if self.config.growth == "logistic":
            if self.config.cap is not None:
                future["cap"] = self.config.cap
            if self.config.floor is not None:
                future["floor"] = self.config.floor

        # Generate forecast
        forecast = model.predict(future)

        # Get date boundaries
        training_end_date = train_data.index.max().strftime("%Y-%m-%d")

        return ForecastResult(
            horizon="backtest",
            forecast_df=forecast,
            model=model,
            training_end_date=training_end_date,
            forecast_start_date=cutoff_date,
            mape=None,  # Will be calculated externally
            rmse=None,
        ), df

    def to_chart_format(
        self,
        forecast_result: ForecastResult,
        horizon_config: ForecastHorizon,
        include_history: bool = True
    ) -> Dict[str, Any]:
        """
        Convert forecast result to chart-friendly format.

        Args:
            forecast_result: The forecast result to convert
            horizon_config: Horizon configuration for colors
            include_history: Whether to include historical fitted values

        Returns:
            Dict with forecast series data for charting
        """
        df = forecast_result.forecast_df
        training_end = pd.to_datetime(forecast_result.training_end_date)

        # Filter to forecast period only (or include history)
        if not include_history:
            df = df[df["ds"] > training_end]

        series = []
        for _, row in df.iterrows():
            # Format timestamp as ISO 8601 with UTC timezone to match candle format
            ts = row["ds"]
            if ts.tzinfo is None:
                # Add UTC timezone if naive
                ts_str = ts.strftime("%Y-%m-%dT00:00:00+00:00")
            else:
                ts_str = ts.isoformat()
            series.append({
                "timestamp": ts_str,
                "value": float(row["yhat"]),
                "lower": float(row["yhat_lower"]),
                "upper": float(row["yhat_upper"]),
                "is_forecast": row["ds"] > training_end,
            })

        return {
            "horizon": horizon_config.name,
            "display_name": horizon_config.display_name,
            "color": horizon_config.color,
            "training_end_date": forecast_result.training_end_date,
            "forecast_start_date": forecast_result.forecast_start_date,
            "mape": forecast_result.mape,
            "rmse": forecast_result.rmse,
            "series": series,
        }
