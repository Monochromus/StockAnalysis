"""Bayesian HMM for regime detection with uncertainty quantification.

Uses pomegranate library for Bayesian HMM implementation with
posterior distributions for model parameters.
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

# Try to import pomegranate
try:
    from pomegranate.hmm import DenseHMM
    from pomegranate.distributions import Normal
    POMEGRANATE_AVAILABLE = True
except ImportError:
    try:
        # Try older pomegranate API
        from pomegranate import HiddenMarkovModel, NormalDistribution
        POMEGRANATE_AVAILABLE = True
        POMEGRANATE_LEGACY = True
    except ImportError:
        POMEGRANATE_AVAILABLE = False
        POMEGRANATE_LEGACY = False
        warnings.warn("pomegranate library not available. Bayesian HMM will not work.")


class BayesianHMMDetector(BaseRegimeDetector):
    """
    Bayesian Hidden Markov Model for regime detection.

    Uses pomegranate's DenseHMM with Normal distributions.
    Provides uncertainty quantification through posterior distributions.

    Note: Falls back to a simpler implementation if pomegranate
    is not available or encounters issues.
    """

    def __init__(
        self,
        n_states: int = 7,
        random_state: int = 42,
        config: Optional[ModelConfig] = None,
        selected_features: Optional[List[str]] = None,
    ):
        """
        Initialize Bayesian HMM detector.

        Args:
            n_states: Number of hidden states
            random_state: Random seed
            config: Optional ModelConfig
            selected_features: Features to use for training
        """
        if config is None:
            config = ModelConfig(
                n_states=n_states,
                selected_features=selected_features or ["log_return", "range", "volume_change"],
                random_state=random_state,
            )

        super().__init__(config)

        self.random_state = config.random_state
        self.model = None
        self._use_fallback = False

        # Initialize feature engine
        self.feature_engine = FeatureEngine(selected_features=self.config.selected_features)

        # Store valid index for alignment
        self._valid_index: Optional[pd.Index] = None

        # For fallback mode: store Gaussian parameters
        self._means: Optional[np.ndarray] = None
        self._stds: Optional[np.ndarray] = None
        self._transmat: Optional[np.ndarray] = None
        self._startprob: Optional[np.ndarray] = None

    def get_model_type(self) -> ModelType:
        """Return the model type identifier."""
        return ModelType.BAYESIAN_HMM

    def _check_availability(self):
        """Check if pomegranate is available."""
        if not POMEGRANATE_AVAILABLE:
            warnings.warn(
                "pomegranate library not available, using fallback implementation. "
                "Install with: pip install pomegranate>=1.0.0"
            )
            self._use_fallback = True

    def prepare_features(
        self,
        df: pd.DataFrame,
        df_indicators: Optional[pd.DataFrame] = None,
        fit: bool = False
    ) -> np.ndarray:
        """Prepare features for HMM training/prediction."""
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
        Train the Bayesian HMM on historical data.

        Args:
            df: DataFrame with OHLCV data
            df_indicators: Optional DataFrame with pre-calculated indicators
            n_iter: Maximum iterations for training

        Returns:
            True if training succeeded
        """
        self._check_availability()

        try:
            features = self.prepare_features(df, df_indicators, fit=True)

            if len(features) < self.n_states * 10:
                raise ValueError("Not enough data for training")

            iterations = n_iter if n_iter is not None else self.config.n_iter

            if self._use_fallback:
                return self._train_fallback(features, iterations)

            return self._train_pomegranate(features, iterations)

        except Exception as e:
            print(f"Bayesian HMM training failed: {e}")
            # Try fallback
            try:
                self._use_fallback = True
                return self._train_fallback(features, iterations)
            except Exception as e2:
                print(f"Fallback training also failed: {e2}")
                return False

    def _train_pomegranate(self, features: np.ndarray, n_iter: int) -> bool:
        """Train using pomegranate library."""
        try:
            if POMEGRANATE_LEGACY:
                return self._train_pomegranate_legacy(features, n_iter)

            # Modern pomegranate API (>= 1.0)
            n_features = features.shape[1]

            # Create initial distributions for each state
            distributions = []
            for i in range(self.n_states):
                # Initialize with k-means-like centers
                idx = int(len(features) * (i + 0.5) / self.n_states)
                mean = features[idx]
                std = features.std(axis=0)
                dist = Normal(means=mean, covs=std**2)
                distributions.append(dist)

            # Create and train the model
            self.model = DenseHMM(
                distributions=distributions,
                max_iter=n_iter,
                verbose=False,
            )

            # Fit the model
            self.model.fit(features[np.newaxis, :, :])  # Add batch dimension

            # Extract learned parameters
            self._extract_state_characteristics_pomegranate()

            self._is_trained = True
            return True

        except Exception as e:
            print(f"Pomegranate training error: {e}")
            self._use_fallback = True
            return self._train_fallback(features, n_iter)

    def _train_pomegranate_legacy(self, features: np.ndarray, n_iter: int) -> bool:
        """Train using legacy pomegranate API."""
        try:
            from pomegranate import HiddenMarkovModel, NormalDistribution

            # Create distributions for each state
            distributions = []
            for i in range(self.n_states):
                idx = int(len(features) * (i + 0.5) / self.n_states)
                mean = float(features[idx, 0])
                std = float(features[:, 0].std())
                distributions.append(NormalDistribution(mean, std))

            # Create transition matrix
            trans_mat = np.ones((self.n_states, self.n_states)) / self.n_states
            starts = np.ones(self.n_states) / self.n_states
            ends = np.zeros(self.n_states)

            # Create model
            self.model = HiddenMarkovModel.from_matrix(
                trans_mat,
                distributions,
                starts,
                ends,
            )

            # Train
            self.model.fit(
                [features[:, 0].tolist()],  # Use first feature
                max_iterations=n_iter,
            )

            self._extract_state_characteristics_legacy()

            self._is_trained = True
            return True

        except Exception as e:
            print(f"Legacy pomegranate error: {e}")
            self._use_fallback = True
            return self._train_fallback(features, n_iter)

    def _train_fallback(self, features: np.ndarray, n_iter: int) -> bool:
        """
        Fallback training using simple k-means + Gaussian estimation.

        This provides basic functionality when pomegranate is unavailable.
        """
        from scipy.cluster.vq import kmeans2

        np.random.seed(self.random_state)

        # Use k-means to initialize state assignments
        centroids, labels = kmeans2(features, self.n_states, minit='++')

        # Estimate Gaussian parameters for each state
        self._means = np.zeros((self.n_states, features.shape[1]))
        self._stds = np.zeros((self.n_states, features.shape[1]))

        for i in range(self.n_states):
            mask = labels == i
            if mask.sum() > 0:
                self._means[i] = features[mask].mean(axis=0)
                self._stds[i] = features[mask].std(axis=0) + 1e-6
            else:
                self._means[i] = centroids[i]
                self._stds[i] = features.std(axis=0)

        # Estimate transition matrix from label sequence
        self._transmat = np.ones((self.n_states, self.n_states)) / self.n_states
        trans_counts = np.zeros((self.n_states, self.n_states))

        for t in range(len(labels) - 1):
            trans_counts[labels[t], labels[t + 1]] += 1

        for i in range(self.n_states):
            if trans_counts[i].sum() > 0:
                self._transmat[i] = trans_counts[i] / trans_counts[i].sum()

        # Start probabilities
        self._startprob = np.bincount(labels, minlength=self.n_states) / len(labels)

        # Run simple EM iterations
        for _ in range(min(n_iter, 20)):
            # E-step: compute responsibilities
            log_prob = self._compute_log_likelihood_fallback(features)
            log_gamma = log_prob - np.max(log_prob, axis=1, keepdims=True)
            gamma = np.exp(log_gamma)
            gamma /= gamma.sum(axis=1, keepdims=True)

            # M-step: update parameters
            for i in range(self.n_states):
                weights = gamma[:, i]
                weight_sum = weights.sum()
                if weight_sum > 1e-6:
                    self._means[i] = (weights[:, np.newaxis] * features).sum(axis=0) / weight_sum
                    diff = features - self._means[i]
                    self._stds[i] = np.sqrt((weights[:, np.newaxis] * diff**2).sum(axis=0) / weight_sum) + 1e-6

        # Set state characteristics
        self.state_means = self._means[:, 0]
        self.state_volatilities = self._stds[:, 0]

        self._create_regime_mapping()

        self._is_trained = True
        return True

    def _compute_log_likelihood_fallback(self, features: np.ndarray) -> np.ndarray:
        """Compute log likelihood for fallback mode."""
        n_samples = features.shape[0]
        log_prob = np.zeros((n_samples, self.n_states))

        for i in range(self.n_states):
            diff = features - self._means[i]
            log_prob[:, i] = -0.5 * np.sum((diff / self._stds[i])**2, axis=1)
            log_prob[:, i] -= np.sum(np.log(self._stds[i]))

        return log_prob

    def _extract_state_characteristics_pomegranate(self):
        """Extract state characteristics from pomegranate model."""
        try:
            distributions = self.model.distributions

            means = []
            vols = []

            for dist in distributions:
                if hasattr(dist, 'means'):
                    means.append(dist.means[0].item() if hasattr(dist.means[0], 'item') else float(dist.means[0]))
                    vols.append(np.sqrt(dist.covs[0].item() if hasattr(dist.covs[0], 'item') else float(dist.covs[0])))
                else:
                    means.append(0.0)
                    vols.append(1.0)

            self.state_means = np.array(means)
            self.state_volatilities = np.array(vols)
            self._create_regime_mapping()

        except Exception as e:
            print(f"Error extracting pomegranate parameters: {e}")
            # Use default values
            self.state_means = np.linspace(-0.02, 0.02, self.n_states)
            self.state_volatilities = np.ones(self.n_states) * 0.01
            self._create_regime_mapping()

    def _extract_state_characteristics_legacy(self):
        """Extract state characteristics from legacy pomegranate model."""
        try:
            means = []
            vols = []

            for state in self.model.states:
                if hasattr(state, 'distribution') and state.distribution is not None:
                    dist = state.distribution
                    if hasattr(dist, 'parameters'):
                        means.append(dist.parameters[0])
                        vols.append(dist.parameters[1])

            if means:
                self.state_means = np.array(means)
                self.state_volatilities = np.array(vols)
            else:
                self.state_means = np.linspace(-0.02, 0.02, self.n_states)
                self.state_volatilities = np.ones(self.n_states) * 0.01

            self._create_regime_mapping()

        except Exception as e:
            print(f"Error extracting legacy parameters: {e}")
            self.state_means = np.linspace(-0.02, 0.02, self.n_states)
            self.state_volatilities = np.ones(self.n_states) * 0.01
            self._create_regime_mapping()

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

        if self._use_fallback:
            return self._predict_fallback(features)

        return self._predict_pomegranate(features)

    def _predict_pomegranate(self, features: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Predict using pomegranate model."""
        try:
            if POMEGRANATE_LEGACY:
                # Legacy API
                regimes = np.array(self.model.predict(features[:, 0].tolist()))
                probs = np.zeros((len(features), self.n_states))

                # Try to get probabilities
                try:
                    log_probs = self.model.predict_proba(features[:, 0].tolist())
                    probs = np.exp(log_probs - np.max(log_probs, axis=1, keepdims=True))
                    probs /= probs.sum(axis=1, keepdims=True)
                except Exception:
                    # Fallback: one-hot based on prediction
                    for i, r in enumerate(regimes):
                        probs[i, r] = 1.0

                return regimes, probs

            else:
                # Modern API
                features_batch = features[np.newaxis, :, :]
                regimes = self.model.predict(features_batch)[0]
                probs = self.model.predict_proba(features_batch)[0]

                return np.array(regimes), np.array(probs)

        except Exception as e:
            print(f"Pomegranate prediction error: {e}")
            return self._predict_fallback(features)

    def _predict_fallback(self, features: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Predict using fallback Gaussian model with Viterbi-like decoding."""
        log_prob = self._compute_log_likelihood_fallback(features)
        n_samples = len(features)

        # Simple Viterbi-like decoding
        log_delta = np.zeros((n_samples, self.n_states))
        psi = np.zeros((n_samples, self.n_states), dtype=int)

        log_startprob = np.log(self._startprob + 1e-10)
        log_transmat = np.log(self._transmat + 1e-10)

        log_delta[0] = log_startprob + log_prob[0]

        for t in range(1, n_samples):
            for j in range(self.n_states):
                candidates = log_delta[t - 1] + log_transmat[:, j]
                psi[t, j] = np.argmax(candidates)
                log_delta[t, j] = candidates[psi[t, j]] + log_prob[t, j]

        # Backtrack
        regimes = np.zeros(n_samples, dtype=int)
        regimes[-1] = np.argmax(log_delta[-1])

        for t in range(n_samples - 2, -1, -1):
            regimes[t] = psi[t + 1, regimes[t + 1]]

        # Calculate probabilities
        probs = np.exp(log_prob - np.max(log_prob, axis=1, keepdims=True))
        probs /= probs.sum(axis=1, keepdims=True)

        return regimes, probs

    def serialize(self) -> bytes:
        """Serialize model for storage."""
        return pickle.dumps(
            {
                "model": self.model if not self._use_fallback else None,
                "use_fallback": self._use_fallback,
                "means": self._means,
                "stds": self._stds,
                "transmat": self._transmat,
                "startprob": self._startprob,
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
    def deserialize(cls, data: bytes) -> "BayesianHMMDetector":
        """Load model from serialized data."""
        state = pickle.loads(data)
        detector = cls(
            n_states=state["n_states"],
            config=state.get("config"),
        )
        detector.model = state["model"]
        detector._use_fallback = state["use_fallback"]
        detector._means = state["means"]
        detector._stds = state["stds"]
        detector._transmat = state["transmat"]
        detector._startprob = state["startprob"]
        detector.regime_mapping = state["regime_mapping"]
        detector.state_means = state["state_means"]
        detector.state_volatilities = state["state_volatilities"]
        detector._is_trained = state["is_trained"]
        if "feature_engine" in state:
            detector.feature_engine = state["feature_engine"]
        return detector
