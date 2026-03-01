"""Hidden Markov Model for market regime detection."""

import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
from typing import Tuple, Optional, Dict, List
import pickle

from .base_detector import (
    BaseRegimeDetector,
    ModelConfig,
    ModelType,
    EmissionDistribution,
    RegimeInfo,
)
from .feature_engine import FeatureEngine


class HMMRegimeDetector(BaseRegimeDetector):
    """
    Gaussian HMM for detecting market regimes.

    Classifies market states into:
    - Bull Run (strong uptrend)
    - Bull (moderate uptrend)
    - Neutral Up (slight upward bias)
    - Chop/Sideways (no clear direction)
    - Neutral Down (slight downward bias)
    - Bear (moderate downtrend)
    - Crash (strong downtrend)
    """

    def __init__(
        self,
        n_states: int = 7,
        random_state: int = 42,
        config: Optional[ModelConfig] = None,
        selected_features: Optional[List[str]] = None,
    ):
        """
        Initialize HMM detector.

        Args:
            n_states: Number of hidden states (default 7)
            random_state: Random seed for reproducibility
            config: Optional ModelConfig (overrides n_states if provided)
            selected_features: Optional list of features to use
        """
        # Create config if not provided
        if config is None:
            config = ModelConfig(
                n_states=n_states,
                selected_features=selected_features or ["log_return", "range", "volume_change"],
                random_state=random_state,
            )
        else:
            # Update n_states from config
            n_states = config.n_states

        super().__init__(config)

        self.random_state = random_state
        self.model: Optional[GaussianHMM] = None

        # Initialize feature engine with selected features
        self.feature_engine = FeatureEngine(selected_features=self.config.selected_features)

        # Store valid index for alignment
        self._valid_index: Optional[pd.Index] = None

    def get_model_type(self) -> ModelType:
        """Return the model type identifier."""
        return ModelType.HMM_GAUSSIAN

    def prepare_features(
        self,
        df: pd.DataFrame,
        df_indicators: Optional[pd.DataFrame] = None,
        fit: bool = False
    ) -> np.ndarray:
        """
        Prepare features for HMM training/prediction.

        Args:
            df: DataFrame with OHLCV data
            df_indicators: Optional DataFrame with pre-calculated indicators
            fit: Whether to fit the scaler (True for training)

        Returns:
            Feature matrix (n_samples, n_features)
        """
        # Extract features using the feature engine
        features_df, valid_index = self.feature_engine.extract_features(df, df_indicators)
        self._valid_index = valid_index

        if fit:
            return self.feature_engine.fit_transform(features_df)
        else:
            return self.feature_engine.transform(features_df)

    def train(
        self,
        df: pd.DataFrame,
        df_indicators: Optional[pd.DataFrame] = None,
        n_iter: Optional[int] = None
    ) -> bool:
        """
        Train the HMM on historical data.

        Args:
            df: DataFrame with OHLCV data
            df_indicators: Optional DataFrame with pre-calculated indicators
            n_iter: Maximum iterations for training (overrides config)

        Returns:
            True if training succeeded
        """
        try:
            features = self.prepare_features(df, df_indicators, fit=True)

            if len(features) < self.n_states * 10:
                raise ValueError("Not enough data for training")

            # Use provided n_iter or fall back to config
            iterations = n_iter if n_iter is not None else self.config.n_iter

            # Initialize and train HMM
            self.model = GaussianHMM(
                n_components=self.n_states,
                covariance_type="full",
                n_iter=iterations,
                random_state=self.random_state,
            )

            self.model.fit(features)

            # Get state characteristics from first feature (assumed to be returns)
            self.state_means = self.model.means_[:, 0]
            self.state_volatilities = np.sqrt(
                np.array([self.model.covars_[i][0, 0] for i in range(self.n_states)])
            )

            # Map states to regime names based on mean returns
            self._create_regime_mapping()

            self._is_trained = True
            return True

        except Exception as e:
            print(f"Training failed: {e}")
            return False

    def predict(
        self,
        df: pd.DataFrame,
        df_indicators: Optional[pd.DataFrame] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict regimes for given data.

        Args:
            df: DataFrame with OHLCV data
            df_indicators: Optional DataFrame with pre-calculated indicators

        Returns:
            Tuple of (regime_ids, probabilities)
        """
        if not self._is_trained:
            raise ValueError("Model not trained")

        features = self.prepare_features(df, df_indicators, fit=False)
        regimes = self.model.predict(features)
        probs = self.model.predict_proba(features)

        return regimes, probs

    def serialize(self) -> bytes:
        """Serialize model for storage."""
        return pickle.dumps(
            {
                "model": self.model,
                "n_states": self.n_states,
                "regime_mapping": self.regime_mapping,
                "state_means": self.state_means,
                "state_volatilities": self.state_volatilities,
                "is_trained": self._is_trained,
                "config": self.config,
                "feature_engine": self.feature_engine,
            }
        )

    @classmethod
    def deserialize(cls, data: bytes) -> "HMMRegimeDetector":
        """Load model from serialized data."""
        state = pickle.loads(data)
        detector = cls(
            n_states=state["n_states"],
            config=state.get("config"),
        )
        detector.model = state["model"]
        detector.regime_mapping = state["regime_mapping"]
        detector.state_means = state["state_means"]
        detector.state_volatilities = state["state_volatilities"]
        detector._is_trained = state["is_trained"]
        if "feature_engine" in state:
            detector.feature_engine = state["feature_engine"]
        return detector


# Backward compatibility alias
RegimeInfo = RegimeInfo
