"""Feature engineering for XGBoost residual correction.

Generates 27 features across 8 categories for XGBoost training.
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Tuple
import logging

from .config import XGBoostConfig

logger = logging.getLogger(__name__)


class XGBoostFeatureEngine:
    """
    Feature engineering for XGBoost residual correction.

    Generates features across categories:
    - Time features (5): month, day_of_week, day_of_year, quarter, week_of_year
    - Lag Residual features (5): residual_lag_1 to residual_lag_5
    - Lag Price features (3): price_lag_1, price_lag_3, price_lag_5
    - Rolling Price features (4): price_rolling_mean/std_7, price_rolling_mean/std_30
    - Rolling Volume features (2): volume_rolling_mean_7, volume_rolling_mean_30
    - Rolling Volatility features (2): volatility_rolling_mean_7, volatility_rolling_mean_30
    - Prophet Components (3): prophet_trend, prophet_seasonal, prophet_trend_slope
    - Market Structure (3): price_momentum_14, volume_price_ratio, volatility_zscore_30

    Total: 27 features
    """

    def __init__(self, config: Optional[XGBoostConfig] = None):
        """Initialize feature engine with configuration."""
        self.config = config or XGBoostConfig()

    def generate_features(
        self,
        df: pd.DataFrame,
        prophet_forecast: pd.DataFrame,
        residuals: pd.Series
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Generate all features for XGBoost training.

        Args:
            df: OHLCV DataFrame with columns [timestamp, open, high, low, close, volume]
            prophet_forecast: Prophet forecast DataFrame with yhat, trend columns
            residuals: Series of residuals (actual - prophet_predicted)

        Returns:
            Tuple of (feature DataFrame, list of feature names)
        """
        # Create base DataFrame with dates
        features = pd.DataFrame()
        features["ds"] = pd.to_datetime(df["timestamp"])

        # Add residuals as target reference
        features["residual"] = residuals.values

        # Generate feature groups based on config
        all_feature_names: List[str] = []

        if self.config.use_time_features:
            time_features, time_names = self._generate_time_features(features["ds"])
            features = pd.concat([features, time_features], axis=1)
            all_feature_names.extend(time_names)

        if self.config.use_lag_features:
            lag_features, lag_names = self._generate_lag_features(
                residuals,
                df["close"].values
            )
            features = pd.concat([features, lag_features], axis=1)
            all_feature_names.extend(lag_names)

        if self.config.use_rolling_features:
            rolling_features, rolling_names = self._generate_rolling_features(df)
            features = pd.concat([features, rolling_features], axis=1)
            all_feature_names.extend(rolling_names)

        if self.config.use_prophet_components:
            prophet_features, prophet_names = self._generate_prophet_features(prophet_forecast)
            features = pd.concat([features, prophet_features], axis=1)
            all_feature_names.extend(prophet_names)

        if self.config.use_market_structure:
            market_features, market_names = self._generate_market_structure_features(df)
            features = pd.concat([features, market_features], axis=1)
            all_feature_names.extend(market_names)

        logger.info(f"Generated {len(all_feature_names)} features")

        return features, all_feature_names

    def _generate_time_features(self, dates: pd.Series) -> Tuple[pd.DataFrame, List[str]]:
        """
        Generate time-based features (5 features).

        Features:
        - month (1-12)
        - day_of_week (0-6)
        - day_of_year (1-366)
        - quarter (1-4)
        - week_of_year (1-53)
        """
        features = pd.DataFrame()
        features["month"] = dates.dt.month
        features["day_of_week"] = dates.dt.dayofweek
        features["day_of_year"] = dates.dt.dayofyear
        features["quarter"] = dates.dt.quarter
        features["week_of_year"] = dates.dt.isocalendar().week.astype(int)

        feature_names = ["month", "day_of_week", "day_of_year", "quarter", "week_of_year"]
        return features, feature_names

    def _generate_lag_features(
        self,
        residuals: pd.Series,
        prices: np.ndarray
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Generate lag features (8 features total).

        Residual lags (5): residual_lag_1 to residual_lag_5
        Price lags (3): price_lag_1, price_lag_3, price_lag_5
        """
        features = pd.DataFrame()
        feature_names = []

        # Residual lags
        for lag in self.config.lag_residual_periods:
            col_name = f"residual_lag_{lag}"
            features[col_name] = residuals.shift(lag).values
            feature_names.append(col_name)

        # Price lags
        prices_series = pd.Series(prices)
        for lag in self.config.lag_price_periods:
            col_name = f"price_lag_{lag}"
            features[col_name] = prices_series.shift(lag).values
            feature_names.append(col_name)

        return features, feature_names

    def _generate_rolling_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """
        Generate rolling window features (8 features).

        Rolling Price (4): price_rolling_mean/std for 7, 30 day windows
        Rolling Volume (2): volume_rolling_mean for 7, 30 day windows
        Rolling Volatility (2): volatility_rolling_mean for 7, 30 day windows
        """
        features = pd.DataFrame()
        feature_names = []

        prices = df["close"]
        volume = df["volume"]

        # Calculate daily returns for volatility
        returns = prices.pct_change()

        for window in self.config.rolling_windows:
            # Price rolling stats
            features[f"price_rolling_mean_{window}"] = prices.rolling(window).mean()
            features[f"price_rolling_std_{window}"] = prices.rolling(window).std()
            feature_names.extend([
                f"price_rolling_mean_{window}",
                f"price_rolling_std_{window}"
            ])

            # Volume rolling mean
            features[f"volume_rolling_mean_{window}"] = volume.rolling(window).mean()
            feature_names.append(f"volume_rolling_mean_{window}")

            # Volatility rolling mean (rolling std of returns)
            features[f"volatility_rolling_mean_{window}"] = returns.rolling(window).std()
            feature_names.append(f"volatility_rolling_mean_{window}")

        return features, feature_names

    def _generate_prophet_features(
        self,
        prophet_forecast: pd.DataFrame
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Generate Prophet component features (3 features).

        Features:
        - prophet_trend: The trend component
        - prophet_seasonal: Combined seasonality (yearly + weekly if available)
        - prophet_trend_slope: Rate of change of trend
        """
        features = pd.DataFrame()
        feature_names = []

        # Trend
        features["prophet_trend"] = prophet_forecast["trend"].values
        feature_names.append("prophet_trend")

        # Combined seasonality
        seasonal = np.zeros(len(prophet_forecast))
        if "yearly" in prophet_forecast.columns:
            seasonal += prophet_forecast["yearly"].values
        if "weekly" in prophet_forecast.columns:
            seasonal += prophet_forecast["weekly"].values
        if "monthly" in prophet_forecast.columns:
            seasonal += prophet_forecast["monthly"].values
        features["prophet_seasonal"] = seasonal
        feature_names.append("prophet_seasonal")

        # Trend slope (rate of change)
        features["prophet_trend_slope"] = pd.Series(
            prophet_forecast["trend"].values
        ).diff().values
        feature_names.append("prophet_trend_slope")

        return features, feature_names

    def _generate_market_structure_features(
        self,
        df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Generate market structure features (3 features).

        Features:
        - price_momentum_14: 14-day price momentum (rate of change)
        - volume_price_ratio: Normalized volume/price ratio
        - volatility_zscore_30: 30-day volatility z-score
        """
        features = pd.DataFrame()
        feature_names = []

        prices = df["close"]
        volume = df["volume"]
        returns = prices.pct_change()

        # 14-day momentum (price change percentage)
        features["price_momentum_14"] = prices.pct_change(14)
        feature_names.append("price_momentum_14")

        # Volume/price ratio (normalized)
        vp_ratio = volume / prices
        features["volume_price_ratio"] = (vp_ratio - vp_ratio.rolling(30).mean()) / vp_ratio.rolling(30).std()
        feature_names.append("volume_price_ratio")

        # Volatility z-score
        volatility = returns.rolling(30).std()
        vol_mean = volatility.rolling(30).mean()
        vol_std = volatility.rolling(30).std()
        features["volatility_zscore_30"] = (volatility - vol_mean) / vol_std
        feature_names.append("volatility_zscore_30")

        return features, feature_names

    def prepare_for_training(
        self,
        features: pd.DataFrame,
        feature_names: List[str]
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare features for XGBoost training.

        Handles NaN values by dropping warmup rows and returns X, y.

        Args:
            features: DataFrame with all features and 'residual' column
            feature_names: List of feature column names

        Returns:
            Tuple of (X features DataFrame, y target Series)
        """
        # Drop rows with NaN (first warmup_rows due to rolling windows)
        clean_features = features.dropna(subset=feature_names + ["residual"])

        logger.info(
            f"Dropped {len(features) - len(clean_features)} rows with NaN values "
            f"(warmup period)"
        )

        X = clean_features[feature_names]
        y = clean_features["residual"]

        return X, y

    def prepare_for_prediction(
        self,
        df: pd.DataFrame,
        prophet_forecast: pd.DataFrame,
        feature_names: List[str]
    ) -> pd.DataFrame:
        """
        Prepare features for prediction (without target).

        Args:
            df: OHLCV DataFrame
            prophet_forecast: Prophet forecast with future dates
            feature_names: List of feature names to generate

        Returns:
            DataFrame with features for prediction
        """
        # Create dummy residuals (zeros for future)
        residuals = pd.Series(np.zeros(len(df)))

        features, _ = self.generate_features(df, prophet_forecast, residuals)

        # For future prediction, we may need to handle missing lags differently
        # Fill NaN with forward fill for prediction
        features[feature_names] = features[feature_names].ffill()

        return features[feature_names]

    def generate_future_features(
        self,
        prophet_forecast: pd.DataFrame,
        feature_names: List[str]
    ) -> pd.DataFrame:
        """
        Generate features for future dates (forecast period).

        Only Time Features and Prophet Components can be computed for future dates.
        Other features (lag, rolling, market) require historical OHLCV data.

        Args:
            prophet_forecast: Prophet forecast DataFrame with future dates (ds, yhat, trend, etc.)
            feature_names: List of feature names to generate

        Returns:
            DataFrame with features for the entire forecast period
        """
        n_future = len(prophet_forecast)

        # Prophet forecast should have 'ds' column with dates
        dates = pd.to_datetime(prophet_forecast["ds"]).reset_index(drop=True)

        features = pd.DataFrame(index=range(n_future))
        features["ds"] = dates.values

        generated_names: List[str] = []

        # Generate Time Features (always available for future dates)
        if self.config.use_time_features:
            time_features, time_names = self._generate_time_features(dates)
            # Reset index to align
            time_features = time_features.reset_index(drop=True)
            for col in time_names:
                features[col] = time_features[col].values
            generated_names.extend(time_names)

        # Generate Prophet Component Features (available from Prophet forecast)
        if self.config.use_prophet_components:
            prophet_features, prophet_names = self._generate_prophet_features(
                prophet_forecast.reset_index(drop=True)
            )
            # Reset index to align
            prophet_features = prophet_features.reset_index(drop=True)
            for col in prophet_names:
                features[col] = prophet_features[col].values
            generated_names.extend(prophet_names)

        # Filter to only requested features that were generated
        available_features = [f for f in feature_names if f in generated_names]

        logger.info(
            f"Generated {len(available_features)} future features for {n_future} rows. "
            f"Available: {available_features}"
        )

        # Return only the features that were requested and generated
        # Fill any missing with forward fill
        result = features[available_features].ffill().fillna(0)

        return result
