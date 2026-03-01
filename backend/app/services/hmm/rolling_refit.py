"""Rolling window refit manager for HMM models.

Provides functionality for periodic model retraining with label consistency
using the Hungarian algorithm for optimal state matching.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

from .base_detector import BaseRegimeDetector, ModelConfig


@dataclass
class RefitResult:
    """Result of a single refit operation."""
    timestamp: pd.Timestamp
    success: bool
    label_mapping: Dict[int, int]
    message: str = ""


@dataclass
class RollingRefitConfig:
    """Configuration for rolling refit."""
    window_size: int = 252  # 1 year of trading days
    refit_interval: int = 63  # Quarterly refit
    min_samples: int = 100  # Minimum samples for training


class RollingRefitManager:
    """
    Manager for periodic model retraining with label consistency.

    Handles rolling window training and uses the Hungarian algorithm
    to match new model states with previous states, ensuring consistent
    regime labels across refits.
    """

    def __init__(
        self,
        window_size: int = 252,
        refit_interval: int = 63,
        min_samples: int = 100,
    ):
        """
        Initialize the rolling refit manager.

        Args:
            window_size: Number of periods in the training window
            refit_interval: Number of periods between refits
            min_samples: Minimum samples required for training
        """
        self.window_size = window_size
        self.refit_interval = refit_interval
        self.min_samples = min_samples

        # Track refit history
        self._refit_history: List[RefitResult] = []
        self._refit_timestamps: List[str] = []
        self._last_refit_idx: int = -1

    def needs_refit(self, current_idx: int) -> bool:
        """
        Check if a refit is needed at the current index.

        Args:
            current_idx: Current data index

        Returns:
            True if refit should be performed
        """
        if self._last_refit_idx < 0:
            # First refit - need enough data for window
            return current_idx >= self.window_size

        return (current_idx - self._last_refit_idx) >= self.refit_interval

    def get_training_window(
        self,
        df: pd.DataFrame,
        current_idx: int
    ) -> Tuple[pd.DataFrame, int, int]:
        """
        Get the training data window.

        Args:
            df: Full DataFrame
            current_idx: Current index in the data

        Returns:
            Tuple of (window_df, start_idx, end_idx)
        """
        end_idx = current_idx
        start_idx = max(0, end_idx - self.window_size)

        window_df = df.iloc[start_idx:end_idx].copy()

        return window_df, start_idx, end_idx

    def execute_refit(
        self,
        old_model: Optional[BaseRegimeDetector],
        new_model: BaseRegimeDetector,
        df: pd.DataFrame,
        df_indicators: Optional[pd.DataFrame],
        current_idx: int,
        n_iter: int = 100,
    ) -> Tuple[BaseRegimeDetector, RefitResult]:
        """
        Execute a model refit.

        Args:
            old_model: Previous model (for state matching), None for first fit
            new_model: New model instance to train
            df: Full DataFrame with OHLCV data
            df_indicators: Optional indicators DataFrame
            current_idx: Current index in the data
            n_iter: Training iterations

        Returns:
            Tuple of (trained_model, RefitResult)
        """
        # Get training window
        window_df, start_idx, end_idx = self.get_training_window(df, current_idx)

        if len(window_df) < self.min_samples:
            return old_model, RefitResult(
                timestamp=df.index[current_idx] if current_idx < len(df) else df.index[-1],
                success=False,
                label_mapping={},
                message=f"Insufficient data: {len(window_df)} < {self.min_samples}",
            )

        # Get indicators window if available
        window_indicators = None
        if df_indicators is not None:
            window_indicators = df_indicators.iloc[start_idx:end_idx].copy()

        # Train new model
        try:
            success = new_model.train(window_df, window_indicators, n_iter=n_iter)

            if not success:
                return old_model, RefitResult(
                    timestamp=df.index[current_idx] if current_idx < len(df) else df.index[-1],
                    success=False,
                    label_mapping={},
                    message="Training failed",
                )

            # Match labels with previous model if exists
            label_mapping = {}
            if old_model is not None and old_model.is_trained:
                label_mapping = self._match_labels(
                    old_model, new_model, window_df, window_indicators
                )
                # Apply mapping to new model's regime mapping
                self._apply_label_mapping(new_model, label_mapping)

            # Record refit
            timestamp = df.index[current_idx] if current_idx < len(df) else df.index[-1]
            self._last_refit_idx = current_idx
            self._refit_timestamps.append(
                timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
            )

            result = RefitResult(
                timestamp=timestamp,
                success=True,
                label_mapping=label_mapping,
                message=f"Refit successful at index {current_idx}",
            )
            self._refit_history.append(result)

            return new_model, result

        except Exception as e:
            return old_model, RefitResult(
                timestamp=df.index[current_idx] if current_idx < len(df) else df.index[-1],
                success=False,
                label_mapping={},
                message=f"Training error: {str(e)}",
            )

    def _match_labels(
        self,
        old_model: BaseRegimeDetector,
        new_model: BaseRegimeDetector,
        df: pd.DataFrame,
        df_indicators: Optional[pd.DataFrame],
    ) -> Dict[int, int]:
        """
        Match new model states to old model states using Hungarian algorithm.

        Uses overlap in predictions on the same data to find optimal matching.

        Args:
            old_model: Previous trained model
            new_model: Newly trained model
            df: Data for prediction
            df_indicators: Optional indicators

        Returns:
            Dictionary mapping new state IDs to old state IDs
        """
        try:
            # Get predictions from both models
            old_regimes, _ = old_model.predict(df, df_indicators)
            new_regimes, _ = new_model.predict(df, df_indicators)

            n_states = new_model.n_states

            # Build confusion matrix (overlap count)
            confusion = np.zeros((n_states, n_states))
            for old_r, new_r in zip(old_regimes, new_regimes):
                if 0 <= old_r < n_states and 0 <= new_r < n_states:
                    confusion[new_r, old_r] += 1

            # Use Hungarian algorithm to find optimal matching
            # We want to maximize overlap, so use negative confusion matrix
            row_ind, col_ind = linear_sum_assignment(-confusion)

            # Create mapping: new_state -> old_state
            mapping = {}
            for new_idx, old_idx in zip(row_ind, col_ind):
                mapping[int(new_idx)] = int(old_idx)

            return mapping

        except Exception as e:
            print(f"Label matching failed: {e}")
            # Return identity mapping
            return {i: i for i in range(new_model.n_states)}

    def _apply_label_mapping(
        self,
        model: BaseRegimeDetector,
        mapping: Dict[int, int]
    ):
        """
        Apply label mapping to model's regime mapping.

        Args:
            model: Model to update
            mapping: New state -> old state mapping
        """
        if not mapping or not model.regime_mapping:
            return

        # Reorder state characteristics based on mapping
        if model.state_means is not None:
            new_means = np.zeros_like(model.state_means)
            for new_idx, old_idx in mapping.items():
                if old_idx < len(new_means):
                    new_means[old_idx] = model.state_means[new_idx]
            model.state_means = new_means

        if model.state_volatilities is not None:
            new_vols = np.zeros_like(model.state_volatilities)
            for new_idx, old_idx in mapping.items():
                if old_idx < len(new_vols):
                    new_vols[old_idx] = model.state_volatilities[new_idx]
            model.state_volatilities = new_vols

        # Recreate regime mapping based on new ordering
        model._create_regime_mapping()

    def run_rolling_analysis(
        self,
        model_factory_fn,
        df: pd.DataFrame,
        df_indicators: Optional[pd.DataFrame],
        n_iter: int = 100,
    ) -> Tuple[BaseRegimeDetector, np.ndarray, np.ndarray]:
        """
        Run complete rolling analysis with periodic refits.

        Args:
            model_factory_fn: Function that creates new model instances
            df: Full DataFrame with OHLCV data
            df_indicators: Optional indicators DataFrame
            n_iter: Training iterations per refit

        Returns:
            Tuple of (final_model, regimes, probabilities)
        """
        n_samples = len(df)

        # Initialize arrays for results
        all_regimes = np.zeros(n_samples, dtype=int)
        all_probs = None  # Will be initialized on first prediction

        current_model = None

        # Iterate through data
        idx = self.window_size  # Start after first window
        while idx <= n_samples:
            if self.needs_refit(idx) or current_model is None:
                # Create new model and refit
                new_model = model_factory_fn()

                current_model, result = self.execute_refit(
                    current_model,
                    new_model,
                    df.iloc[:idx],
                    df_indicators.iloc[:idx] if df_indicators is not None else None,
                    idx - 1,  # Use last index in current data
                    n_iter,
                )

                if not result.success and current_model is None:
                    # Skip ahead if initial training fails
                    idx += self.refit_interval
                    continue

            # Predict for current segment
            if current_model is not None and current_model.is_trained:
                segment_end = min(idx + self.refit_interval, n_samples)
                segment_df = df.iloc[:segment_end]
                segment_indicators = df_indicators.iloc[:segment_end] if df_indicators is not None else None

                try:
                    regimes, probs = current_model.predict(segment_df, segment_indicators)

                    # Initialize probability array if needed
                    if all_probs is None:
                        all_probs = np.zeros((n_samples, current_model.n_states))

                    # Store results for new predictions only
                    new_start = max(idx - self.refit_interval, self.window_size - 1)
                    new_end = len(regimes)
                    all_regimes[new_start:segment_end] = regimes[new_start - (segment_end - len(regimes)):]

                    if new_end <= len(probs):
                        all_probs[new_start:segment_end] = probs[new_start - (segment_end - len(regimes)):new_end]

                except Exception as e:
                    print(f"Prediction error at index {idx}: {e}")

            idx += self.refit_interval

        # Final prediction with last model
        if current_model is not None and current_model.is_trained:
            try:
                all_regimes_final, all_probs_final = current_model.predict(df, df_indicators)
                return current_model, all_regimes_final, all_probs_final
            except Exception:
                pass

        if all_probs is None:
            all_probs = np.zeros((n_samples, 7))  # Default 7 states

        return current_model, all_regimes, all_probs

    def get_refit_timestamps(self) -> List[str]:
        """Get list of refit timestamps."""
        return self._refit_timestamps.copy()

    def get_refit_history(self) -> List[RefitResult]:
        """Get list of all refit results."""
        return self._refit_history.copy()

    def reset(self):
        """Reset refit history."""
        self._refit_history = []
        self._refit_timestamps = []
        self._last_refit_idx = -1
