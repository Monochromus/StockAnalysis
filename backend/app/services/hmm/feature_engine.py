"""Feature engineering for HMM regime detection."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


@dataclass
class FeatureConfig:
    """Configuration for feature selection."""
    # Basic OHLCV features
    log_return: bool = True
    range: bool = True
    volume_change: bool = True

    # Momentum features
    rsi: bool = False
    macd: bool = False
    macd_histogram: bool = False
    momentum_normalized: bool = False
    roc: bool = False

    # Trend features
    adx: bool = False
    di_diff: bool = False

    # Volatility features
    bb_pct: bool = False
    atr_normalized: bool = False

    # Moving average distance features
    sma_20_dist: bool = False
    sma_50_dist: bool = False
    sma_200_dist: bool = False

    # Volume features
    volume_ratio: bool = False


class FeatureEngine:
    """
    Feature engineering for regime detection models.

    Extracts and normalizes features from OHLCV data and technical indicators.
    Supports multivariate feature selection for different model configurations.
    """

    # All available features with their sources
    AVAILABLE_FEATURES = [
        # Basic OHLCV-derived features
        "log_return",       # Log returns
        "range",            # (High-Low) / Close
        "volume_change",    # Volume percent change

        # Momentum indicators
        "rsi",              # Relative Strength Index
        "macd",             # MACD line value
        "macd_histogram",   # MACD histogram
        "momentum_normalized",  # Normalized momentum
        "roc",              # Rate of Change

        # Trend indicators
        "adx",              # Average Directional Index
        "di_diff",          # DI+ - DI- (directional indicator difference)

        # Volatility indicators
        "bb_pct",           # Bollinger Bands %B
        "atr_normalized",   # Normalized ATR

        # Moving average distance (normalized)
        "sma_20_dist",      # Distance from SMA 20
        "sma_50_dist",      # Distance from SMA 50
        "sma_200_dist",     # Distance from SMA 200

        # Volume indicators
        "volume_ratio",     # Volume / Volume SMA
    ]

    # Warmup periods required for each feature
    FEATURE_WARMUP_PERIODS: Dict[str, int] = {
        "log_return": 1,
        "range": 0,
        "volume_change": 1,
        "rsi": 14,
        "macd": 26,
        "macd_histogram": 26,
        "adx": 14,
        "di_diff": 14,
        "bb_pct": 20,
        "atr_normalized": 14,
        "momentum_normalized": 10,
        "roc": 10,
        "volume_ratio": 20,
        "sma_20_dist": 20,
        "sma_50_dist": 50,
        "sma_200_dist": 200,
    }

    # Features that require indicator DataFrame vs OHLCV only
    OHLCV_FEATURES = {"log_return", "range", "volume_change"}
    INDICATOR_FEATURES = {
        "rsi", "macd", "macd_histogram", "adx", "di_diff",
        "bb_pct", "atr_normalized", "momentum_normalized", "roc",
        "volume_ratio", "sma_20_dist", "sma_50_dist", "sma_200_dist"
    }

    def __init__(self, selected_features: Optional[List[str]] = None):
        """
        Initialize the feature engine.

        Args:
            selected_features: List of feature names to extract.
                             Defaults to basic features if not provided.
        """
        if selected_features is None:
            selected_features = ["log_return", "range", "volume_change"]

        # Validate features
        invalid = set(selected_features) - set(self.AVAILABLE_FEATURES)
        if invalid:
            raise ValueError(f"Invalid features: {invalid}")

        self.selected_features = selected_features
        self.scaler = StandardScaler()
        self._is_fitted = False

    def get_selected_features(self) -> List[str]:
        """Return the list of selected features."""
        return self.selected_features

    def get_warmup_period(self) -> int:
        """
        Calculate the warmup period required for selected features.

        Returns:
            Maximum warmup period needed across all selected features.
        """
        return max(
            self.FEATURE_WARMUP_PERIODS.get(f, 0)
            for f in self.selected_features
        )

    def requires_indicators(self) -> bool:
        """Check if any selected feature requires indicator DataFrame."""
        return bool(set(self.selected_features) & self.INDICATOR_FEATURES)

    def extract_features(
        self,
        df: pd.DataFrame,
        df_indicators: Optional[pd.DataFrame] = None
    ) -> Tuple[pd.DataFrame, pd.Index]:
        """
        Extract selected features from data.

        Args:
            df: DataFrame with OHLCV data (Open, High, Low, Close, Volume)
            df_indicators: DataFrame with pre-calculated indicators (optional)

        Returns:
            Tuple of (features_df, valid_index) where valid_index contains
            timestamps with complete data.
        """
        features = pd.DataFrame(index=df.index)

        # Extract OHLCV-based features
        if "log_return" in self.selected_features:
            features["log_return"] = np.log(df["Close"] / df["Close"].shift(1))

        if "range" in self.selected_features:
            features["range"] = (df["High"] - df["Low"]) / df["Close"]

        if "volume_change" in self.selected_features:
            features["volume_change"] = df["Volume"].pct_change()

        # Extract indicator-based features if available
        if df_indicators is not None:
            # Momentum features
            if "rsi" in self.selected_features and "rsi" in df_indicators.columns:
                # Normalize RSI to [-1, 1] range centered at 50
                features["rsi"] = (df_indicators["rsi"] - 50) / 50

            if "macd" in self.selected_features and "macd" in df_indicators.columns:
                features["macd"] = df_indicators["macd"]

            if "macd_histogram" in self.selected_features and "macd_histogram" in df_indicators.columns:
                features["macd_histogram"] = df_indicators["macd_histogram"]

            if "momentum_normalized" in self.selected_features and "momentum" in df_indicators.columns:
                # Normalize momentum relative to price
                features["momentum_normalized"] = df_indicators["momentum"] / df["Close"]

            if "roc" in self.selected_features and "roc" in df_indicators.columns:
                features["roc"] = df_indicators["roc"] / 100  # Convert to decimal

            # Trend features
            if "adx" in self.selected_features and "adx" in df_indicators.columns:
                features["adx"] = df_indicators["adx"] / 100  # Normalize to [0, 1]

            if "di_diff" in self.selected_features:
                if "di_plus" in df_indicators.columns and "di_minus" in df_indicators.columns:
                    features["di_diff"] = (df_indicators["di_plus"] - df_indicators["di_minus"]) / 100

            # Volatility features
            if "bb_pct" in self.selected_features and "bb_pct" in df_indicators.columns:
                # bb_pct is already in [0, 1] range typically
                features["bb_pct"] = df_indicators["bb_pct"]

            if "atr_normalized" in self.selected_features and "atr" in df_indicators.columns:
                # Normalize ATR by close price
                features["atr_normalized"] = df_indicators["atr"] / df["Close"]

            # Volume features
            if "volume_ratio" in self.selected_features and "volume_ratio" in df_indicators.columns:
                features["volume_ratio"] = df_indicators["volume_ratio"] - 1  # Center at 0

            # Moving average distance features
            if "sma_20_dist" in self.selected_features and "sma_20" in df_indicators.columns:
                features["sma_20_dist"] = (df["Close"] - df_indicators["sma_20"]) / df_indicators["sma_20"]

            if "sma_50_dist" in self.selected_features and "sma_50" in df_indicators.columns:
                features["sma_50_dist"] = (df["Close"] - df_indicators["sma_50"]) / df_indicators["sma_50"]

            if "sma_200_dist" in self.selected_features and "sma_200" in df_indicators.columns:
                features["sma_200_dist"] = (df["Close"] - df_indicators["sma_200"]) / df_indicators["sma_200"]

        # Only keep selected features that were successfully extracted
        available_cols = [f for f in self.selected_features if f in features.columns]
        features = features[available_cols]

        # Drop rows with NaN values
        valid_mask = features.notna().all(axis=1)
        valid_index = features.index[valid_mask]
        features = features.loc[valid_index]

        # Clip extreme values (1st and 99th percentile)
        for col in features.columns:
            lower = features[col].quantile(0.01)
            upper = features[col].quantile(0.99)
            features[col] = features[col].clip(lower, upper)

        return features, valid_index

    def fit_transform(self, features: pd.DataFrame) -> np.ndarray:
        """
        Fit the scaler and transform features.

        Args:
            features: DataFrame of extracted features

        Returns:
            Scaled feature matrix (n_samples, n_features)
        """
        scaled = self.scaler.fit_transform(features.values)
        self._is_fitted = True
        return scaled

    def transform(self, features: pd.DataFrame) -> np.ndarray:
        """
        Transform features using fitted scaler.

        Args:
            features: DataFrame of extracted features

        Returns:
            Scaled feature matrix (n_samples, n_features)

        Raises:
            RuntimeError: If scaler has not been fitted
        """
        if not self._is_fitted:
            raise RuntimeError("Scaler not fitted. Call fit_transform first.")
        return self.scaler.transform(features.values)

    @property
    def is_fitted(self) -> bool:
        """Check if the scaler has been fitted."""
        return self._is_fitted

    @classmethod
    def from_config(cls, config: FeatureConfig) -> "FeatureEngine":
        """
        Create a FeatureEngine from a FeatureConfig.

        Args:
            config: FeatureConfig with boolean flags for each feature

        Returns:
            Configured FeatureEngine instance
        """
        selected = []
        for feature in cls.AVAILABLE_FEATURES:
            if getattr(config, feature, False):
                selected.append(feature)

        if not selected:
            # Default to basic features
            selected = ["log_return", "range", "volume_change"]

        return cls(selected_features=selected)
