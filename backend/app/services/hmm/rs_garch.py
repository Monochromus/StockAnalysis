"""Regime-Switching GARCH model for volatility-based regime detection.

Uses the arch library to fit GARCH(1,1) with Student-t distribution
and assigns regimes based on conditional volatility quantiles.
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, List
import pickle
import warnings

from .base_detector import (
    BaseRegimeDetector,
    ModelConfig,
    ModelType,
    RegimeInfo,
)
from .feature_engine import FeatureEngine

# Try to import arch library
try:
    from arch import arch_model
    ARCH_AVAILABLE = True
except ImportError:
    ARCH_AVAILABLE = False
    warnings.warn("arch library not available. RS-GARCH model will not work.")


class RSGARCHDetector(BaseRegimeDetector):
    """
    Regime-Switching GARCH detector.

    Uses GARCH(1,1) with Student-t distribution to model conditional
    volatility, then assigns regimes based on volatility quantiles
    and return direction.

    Regime assignment:
    - High volatility + negative returns = Crash/Bear regimes
    - High volatility + positive returns = Bull Run regime
    - Low volatility + positive returns = Bull regime
    - Low volatility + negative returns = Neutral Down regime
    - Medium volatility = Chop/Neutral regimes
    """

    def __init__(
        self,
        n_states: int = 7,
        random_state: int = 42,
        config: Optional[ModelConfig] = None,
        selected_features: Optional[List[str]] = None,
    ):
        """
        Initialize RS-GARCH detector.

        Args:
            n_states: Number of regimes (should be 7 for standard mapping)
            random_state: Random seed
            config: Optional ModelConfig
            selected_features: Features for additional analysis (not used for GARCH)
        """
        if config is None:
            config = ModelConfig(
                n_states=n_states,
                selected_features=selected_features or ["log_return"],
                random_state=random_state,
            )

        super().__init__(config)

        self.random_state = config.random_state
        self.garch_model = None
        self.garch_fit = None

        # Volatility quantiles for regime assignment
        self._volatility_quantiles: Optional[np.ndarray] = None
        self._return_quantiles: Optional[np.ndarray] = None

        # Store training data stats
        self._valid_index: Optional[pd.Index] = None

    def get_model_type(self) -> ModelType:
        """Return the model type identifier."""
        return ModelType.RS_GARCH

    def _check_availability(self):
        """Check if arch library is available."""
        if not ARCH_AVAILABLE:
            raise ImportError(
                "arch library is required for RS-GARCH model. "
                "Install with: pip install arch"
            )

    def train(
        self,
        df: pd.DataFrame,
        df_indicators: Optional[pd.DataFrame] = None,
        n_iter: Optional[int] = None
    ) -> bool:
        """
        Train the GARCH model on historical data.

        Args:
            df: DataFrame with OHLCV data
            df_indicators: Not used for GARCH
            n_iter: Not used for GARCH (uses internal optimization)

        Returns:
            True if training succeeded
        """
        self._check_availability()

        try:
            # Calculate returns
            returns = 100 * np.log(df["Close"] / df["Close"].shift(1)).dropna()
            self._valid_index = returns.index

            if len(returns) < 100:
                raise ValueError("Not enough data for GARCH training (need at least 100 points)")

            # Fit GARCH(1,1) with Student-t distribution
            self.garch_model = arch_model(
                returns,
                vol="Garch",
                p=1,
                q=1,
                dist="t",  # Student-t distribution
            )

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.garch_fit = self.garch_model.fit(disp="off")

            # Get conditional volatility
            cond_vol = self.garch_fit.conditional_volatility

            # Calculate quantiles for regime assignment
            self._volatility_quantiles = np.percentile(cond_vol, [20, 40, 60, 80])
            self._return_quantiles = np.percentile(returns, [20, 40, 60, 80])

            # Calculate state characteristics
            self._calculate_state_characteristics(returns, cond_vol)

            # Create regime mapping
            self._create_regime_mapping()

            self._is_trained = True
            return True

        except Exception as e:
            print(f"RS-GARCH training failed: {e}")
            return False

    def _calculate_state_characteristics(self, returns: pd.Series, volatility: pd.Series):
        """Calculate mean return and volatility for each regime."""
        regimes = self._assign_regimes(returns.values, volatility.values)

        self.state_means = np.zeros(self.n_states)
        self.state_volatilities = np.zeros(self.n_states)

        for i in range(self.n_states):
            mask = regimes == i
            if mask.sum() > 0:
                self.state_means[i] = returns.values[mask].mean() / 100  # Convert back from percentage
                self.state_volatilities[i] = volatility.values[mask].mean() / 100

    def _assign_regimes(self, returns: np.ndarray, volatility: np.ndarray) -> np.ndarray:
        """
        Assign regimes based on returns and volatility.

        Regime mapping for 7 states:
        0: Crash - Very high volatility, very negative returns
        1: Bear - High volatility, negative returns
        2: Neutral Down - Medium volatility, slightly negative returns
        3: Chop - Any volatility, near-zero returns
        4: Neutral Up - Medium volatility, slightly positive returns
        5: Bull - Low-medium volatility, positive returns
        6: Bull Run - High volatility, very positive returns
        """
        n_samples = len(returns)
        regimes = np.full(n_samples, 3)  # Default to Chop

        if self._volatility_quantiles is None or self._return_quantiles is None:
            return regimes

        vq = self._volatility_quantiles
        rq = self._return_quantiles

        for i in range(n_samples):
            vol = volatility[i]
            ret = returns[i]

            # Very negative returns
            if ret < rq[0]:
                if vol > vq[3]:  # Very high volatility
                    regimes[i] = 0  # Crash
                elif vol > vq[2]:  # High volatility
                    regimes[i] = 1  # Bear
                else:
                    regimes[i] = 2  # Neutral Down

            # Slightly negative returns
            elif ret < rq[1]:
                if vol > vq[3]:
                    regimes[i] = 1  # Bear
                else:
                    regimes[i] = 2  # Neutral Down

            # Near-zero returns (Chop)
            elif ret < rq[2]:
                regimes[i] = 3  # Chop

            # Slightly positive returns
            elif ret < rq[3]:
                if vol > vq[3]:
                    regimes[i] = 6  # Bull Run (high vol + positive)
                else:
                    regimes[i] = 4  # Neutral Up

            # Very positive returns
            else:
                if vol > vq[2]:  # High volatility
                    regimes[i] = 6  # Bull Run
                else:
                    regimes[i] = 5  # Bull

        return regimes

    def predict(
        self,
        df: pd.DataFrame,
        df_indicators: Optional[pd.DataFrame] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict regimes for given data.

        Args:
            df: DataFrame with OHLCV data
            df_indicators: Not used

        Returns:
            Tuple of (regime_ids, probabilities)
        """
        self._check_availability()

        if not self._is_trained:
            raise ValueError("Model not trained")

        # Calculate returns
        returns = 100 * np.log(df["Close"] / df["Close"].shift(1)).dropna()

        # Forecast volatility using the fitted model
        # For simplicity, we'll use a rolling forecast approach
        forecasts = self.garch_fit.forecast(horizon=1, start=0, reindex=False)

        # Handle the case where forecast output differs by arch version
        if hasattr(forecasts, 'variance'):
            cond_var = forecasts.variance.values.flatten()
        else:
            # Fall back to using fitted conditional volatility for in-sample
            cond_var = self.garch_fit.conditional_volatility.values ** 2

        # Ensure alignment
        min_len = min(len(returns), len(cond_var))
        returns_vals = returns.values[-min_len:]
        cond_vol = np.sqrt(cond_var[-min_len:])

        self._valid_index = returns.index[-min_len:]

        # Assign regimes
        regimes = self._assign_regimes(returns_vals, cond_vol)

        # Calculate pseudo-probabilities based on distance to regime centroids
        probs = self._calculate_pseudo_probabilities(returns_vals, cond_vol, regimes)

        return regimes, probs

    def _calculate_pseudo_probabilities(
        self,
        returns: np.ndarray,
        volatility: np.ndarray,
        regimes: np.ndarray
    ) -> np.ndarray:
        """
        Calculate pseudo-probabilities for regime assignment.

        Since GARCH doesn't provide state probabilities like HMM,
        we estimate them based on feature similarity to regime centroids.
        """
        n_samples = len(returns)
        probs = np.zeros((n_samples, self.n_states))

        # Create feature matrix
        features = np.column_stack([returns, volatility])

        # Calculate regime centroids
        centroids = np.zeros((self.n_states, 2))
        for i in range(self.n_states):
            mask = regimes == i
            if mask.sum() > 0:
                centroids[i] = features[mask].mean(axis=0)
            else:
                centroids[i] = [self.state_means[i] * 100, self.state_volatilities[i] * 100]

        # Calculate distances and convert to probabilities
        for t in range(n_samples):
            distances = np.linalg.norm(features[t] - centroids, axis=1)
            # Convert to probabilities using softmax on negative distances
            exp_neg_dist = np.exp(-distances / (distances.std() + 1e-6))
            probs[t] = exp_neg_dist / exp_neg_dist.sum()

        return probs

    def get_regime_series(self, df: pd.DataFrame, df_indicators: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Get regime predictions as a DataFrame."""
        regimes, probs = self.predict(df, df_indicators)

        result = pd.DataFrame(index=self._valid_index)
        result["regime_id"] = regimes
        result["regime_name"] = [
            self.regime_mapping.get(r, f"State_{r}") for r in regimes
        ]
        result["confidence"] = [probs[i, regimes[i]] for i in range(len(regimes))]

        return result

    def serialize(self) -> bytes:
        """Serialize model for storage."""
        return pickle.dumps(
            {
                "garch_fit": self.garch_fit,
                "n_states": self.n_states,
                "regime_mapping": self.regime_mapping,
                "state_means": self.state_means,
                "state_volatilities": self.state_volatilities,
                "volatility_quantiles": self._volatility_quantiles,
                "return_quantiles": self._return_quantiles,
                "is_trained": self._is_trained,
                "config": self.config,
            }
        )

    @classmethod
    def deserialize(cls, data: bytes) -> "RSGARCHDetector":
        """Load model from serialized data."""
        state = pickle.loads(data)
        detector = cls(
            n_states=state["n_states"],
            config=state.get("config"),
        )
        detector.garch_fit = state["garch_fit"]
        detector.regime_mapping = state["regime_mapping"]
        detector.state_means = state["state_means"]
        detector.state_volatilities = state["state_volatilities"]
        detector._volatility_quantiles = state["volatility_quantiles"]
        detector._return_quantiles = state["return_quantiles"]
        detector._is_trained = state["is_trained"]
        return detector
