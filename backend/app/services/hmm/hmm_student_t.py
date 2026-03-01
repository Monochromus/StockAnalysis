"""Student-t HMM Regime Detector wrapper."""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, List
import pickle

from .base_detector import (
    BaseRegimeDetector,
    ModelConfig,
    ModelType,
    RegimeInfo,
)
from .feature_engine import FeatureEngine
from .student_t_hmm import StudentTHMM


class StudentTRegimeDetector(BaseRegimeDetector):
    """
    Hidden Markov Model with Student-t emissions for regime detection.

    The Student-t distribution has heavier tails than Gaussian,
    making it more robust to extreme returns common in financial markets.
    """

    def __init__(
        self,
        n_states: int = 7,
        df: float = 5.0,
        random_state: int = 42,
        config: Optional[ModelConfig] = None,
        selected_features: Optional[List[str]] = None,
    ):
        """
        Initialize Student-t HMM detector.

        Args:
            n_states: Number of hidden states (default 7)
            df: Degrees of freedom for Student-t (lower = heavier tails)
            random_state: Random seed for reproducibility
            config: Optional ModelConfig (overrides n_states/df if provided)
            selected_features: Optional list of features to use
        """
        if config is None:
            config = ModelConfig(
                n_states=n_states,
                student_t_df=df,
                selected_features=selected_features or ["log_return", "range", "volume_change"],
                random_state=random_state,
            )

        super().__init__(config)

        self.df = config.student_t_df
        self.random_state = config.random_state
        self.model: Optional[StudentTHMM] = None

        # Initialize feature engine
        self.feature_engine = FeatureEngine(selected_features=self.config.selected_features)

        # Store valid index for alignment
        self._valid_index: Optional[pd.Index] = None

    def get_model_type(self) -> ModelType:
        """Return the model type identifier."""
        return ModelType.HMM_STUDENT_T

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
        Train the Student-t HMM on historical data.

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

            iterations = n_iter if n_iter is not None else self.config.n_iter

            # Initialize and train Student-t HMM
            self.model = StudentTHMM(
                n_components=self.n_states,
                df=self.df,
                covariance_type="full",
                n_iter=iterations,
                random_state=self.random_state,
            )

            self.model.fit(features)

            # Get state characteristics from first feature (returns)
            self.state_means = self.model.means_[:, 0]
            self.state_volatilities = np.sqrt(
                np.array([self.model.covars_[i][0, 0] for i in range(self.n_states)])
            )

            # Map states to regime names
            self._create_regime_mapping()

            self._is_trained = True
            return True

        except Exception as e:
            print(f"Student-t HMM training failed: {e}")
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
                "df": self.df,
                "regime_mapping": self.regime_mapping,
                "state_means": self.state_means,
                "state_volatilities": self.state_volatilities,
                "is_trained": self._is_trained,
                "config": self.config,
                "feature_engine": self.feature_engine,
            }
        )

    @classmethod
    def deserialize(cls, data: bytes) -> "StudentTRegimeDetector":
        """Load model from serialized data."""
        state = pickle.loads(data)
        detector = cls(
            n_states=state["n_states"],
            df=state.get("df", 5.0),
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
