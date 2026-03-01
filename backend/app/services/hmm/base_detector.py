"""Abstract base class for regime detection models."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


class EmissionDistribution(str, Enum):
    """Emission distribution types for HMM models."""
    GAUSSIAN = "gaussian"
    STUDENT_T = "student_t"


class ModelType(str, Enum):
    """Available model types for regime detection."""
    HMM_GAUSSIAN = "hmm_gaussian"
    HMM_STUDENT_T = "hmm_student_t"
    RS_GARCH = "rs_garch"
    BAYESIAN_HMM = "bayesian_hmm"


@dataclass
class ModelConfig:
    """Configuration for regime detection models."""
    n_states: int = 7
    emission: EmissionDistribution = EmissionDistribution.GAUSSIAN
    student_t_df: float = 5.0
    selected_features: List[str] = field(
        default_factory=lambda: ["log_return", "range", "volume_change"]
    )
    rolling_window_size: int = 252  # 1 year of trading days
    refit_interval: int = 63  # Quarterly
    n_iter: int = 100
    random_state: int = 42


@dataclass
class RegimeInfo:
    """Information about a detected regime."""
    regime_id: int
    regime_name: str
    confidence: float
    mean_return: float
    volatility: float


class BaseRegimeDetector(ABC):
    """
    Abstract base class for market regime detection models.

    Classifies market states into regimes (e.g., Bull, Bear, Chop).
    All concrete implementations must inherit from this class.
    """

    # Default regime names for 7 states
    REGIME_NAMES = {
        0: "Crash",
        1: "Bear",
        2: "Neutral Down",
        3: "Chop",
        4: "Neutral Up",
        5: "Bull",
        6: "Bull Run",
    }

    REGIME_COLORS = {
        "Crash": "#FF0000",
        "Bear": "#FF6B6B",
        "Neutral Down": "#FFB4B4",
        "Chop": "#808080",
        "Neutral Up": "#B4FFB4",
        "Bull": "#6BFF6B",
        "Bull Run": "#00FF00",
    }

    def __init__(self, config: Optional[ModelConfig] = None):
        """
        Initialize the detector.

        Args:
            config: Model configuration. Uses defaults if not provided.
        """
        self.config = config or ModelConfig()
        self.n_states = self.config.n_states
        self.regime_mapping: Dict[int, str] = {}
        self.state_means: Optional[np.ndarray] = None
        self.state_volatilities: Optional[np.ndarray] = None
        self._is_trained = False

    @abstractmethod
    def train(self, df: pd.DataFrame, df_indicators: Optional[pd.DataFrame] = None) -> bool:
        """
        Train the model on historical data.

        Args:
            df: DataFrame with OHLCV data
            df_indicators: Optional DataFrame with pre-calculated indicators

        Returns:
            True if training succeeded
        """
        pass

    @abstractmethod
    def predict(self, df: pd.DataFrame, df_indicators: Optional[pd.DataFrame] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict regimes for given data.

        Args:
            df: DataFrame with OHLCV data
            df_indicators: Optional DataFrame with pre-calculated indicators

        Returns:
            Tuple of (regime_ids, probabilities)
        """
        pass

    @abstractmethod
    def get_model_type(self) -> ModelType:
        """Return the model type identifier."""
        pass

    def _create_regime_mapping(self):
        """Map model states to regime names based on return characteristics."""
        if self.state_means is None:
            return

        # Sort states by mean return
        sorted_indices = np.argsort(self.state_means)

        if self.n_states == 7:
            # Standard 7-state mapping
            mapping = {
                sorted_indices[0]: "Crash",
                sorted_indices[1]: "Bear",
                sorted_indices[2]: "Neutral Down",
                sorted_indices[3]: "Chop",
                sorted_indices[4]: "Neutral Up",
                sorted_indices[5]: "Bull",
                sorted_indices[6]: "Bull Run",
            }
        else:
            # Generic mapping for different number of states
            mapping = {}
            for i, idx in enumerate(sorted_indices):
                if i < self.n_states // 3:
                    mapping[idx] = f"Bear_{i}"
                elif i < 2 * self.n_states // 3:
                    mapping[idx] = f"Neutral_{i}"
                else:
                    mapping[idx] = f"Bull_{i}"

        self.regime_mapping = mapping

    def get_current_regime(self, df: pd.DataFrame, df_indicators: Optional[pd.DataFrame] = None) -> RegimeInfo:
        """
        Get the current (most recent) regime.

        Args:
            df: DataFrame with OHLCV data
            df_indicators: Optional DataFrame with pre-calculated indicators

        Returns:
            RegimeInfo for current state
        """
        regimes, probs = self.predict(df, df_indicators)

        current_regime = regimes[-1]
        current_probs = probs[-1]

        return RegimeInfo(
            regime_id=int(current_regime),
            regime_name=self.regime_mapping.get(current_regime, f"State_{current_regime}"),
            confidence=float(current_probs[current_regime]),
            mean_return=float(self.state_means[current_regime] * 100) if self.state_means is not None else 0.0,
            volatility=float(self.state_volatilities[current_regime] * 100) if self.state_volatilities is not None else 0.0,
        )

    def get_regime_series(self, df: pd.DataFrame, df_indicators: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Get regime predictions as a DataFrame.

        Args:
            df: DataFrame with OHLCV data
            df_indicators: Optional DataFrame with pre-calculated indicators

        Returns:
            DataFrame with regime info aligned to price data
        """
        regimes, probs = self.predict(df, df_indicators)

        # Align with original data (features may have fewer rows due to warmup)
        result = pd.DataFrame(index=df.index[-len(regimes):])

        result["regime_id"] = regimes
        result["regime_name"] = [
            self.regime_mapping.get(r, f"State_{r}") for r in regimes
        ]
        result["confidence"] = [probs[i, regimes[i]] for i in range(len(regimes))]

        return result

    def get_regime_series_as_list(self, df: pd.DataFrame, df_indicators: Optional[pd.DataFrame] = None) -> List[Dict]:
        """
        Get regime predictions as a list of dicts for JSON serialization.

        Args:
            df: DataFrame with OHLCV data
            df_indicators: Optional DataFrame with pre-calculated indicators

        Returns:
            List of regime data points
        """
        regime_df = self.get_regime_series(df, df_indicators)
        result = []

        for idx, row in regime_df.iterrows():
            result.append({
                "timestamp": idx.isoformat() if hasattr(idx, "isoformat") else str(idx),
                "regime_id": int(row["regime_id"]),
                "regime_name": row["regime_name"],
                "confidence": float(row["confidence"]),
                "color": self.REGIME_COLORS.get(row["regime_name"], "#808080"),
            })

        return result

    @property
    def is_trained(self) -> bool:
        """Check if the model has been trained."""
        return self._is_trained
