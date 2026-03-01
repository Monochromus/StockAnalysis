"""
Rolling DFA Calculator.

Provides efficient rolling window DFA calculation with caching and
incremental updates for real-time analysis.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Deque
from collections import deque
from datetime import datetime
import numpy as np

from .calculator import DFACalculator, DFAResult


@dataclass
class RollingDFAState:
    """State of the rolling DFA calculation."""

    current_alpha: float
    """Most recent raw alpha value."""

    ewma_alpha: float
    """EWMA-smoothed alpha value."""

    r_squared: float
    """R² of the most recent DFA fit."""

    alpha_history: List[float] = field(default_factory=list)
    """History of alpha values for analysis."""

    alpha_std: float = 0.0
    """Standard deviation of recent alpha values."""

    last_update: Optional[datetime] = None
    """Timestamp of last update."""


@dataclass
class AlphaHistoryEntry:
    """Entry in the alpha history."""

    timestamp: datetime
    alpha: float
    r_squared: float
    ewma_alpha: float


class RollingDFA:
    """
    Calculates DFA over a rolling window with EWMA smoothing.

    This class maintains state for efficient incremental updates and
    provides smoothed alpha values suitable for adaptive threshold calculation.

    The EWMA smoothing uses adaptive lambda:
    - When alpha changes significantly (regime transition), use faster lambda
    - When alpha is stable, use slower lambda for smoothness

    Args:
        window_size: Number of data points for DFA calculation.
        polynomial_order: Order of polynomial for DFA detrending.
        ewma_lambda_slow: EWMA decay factor for stable conditions.
        ewma_lambda_fast: EWMA decay factor for regime transitions.
        regime_change_threshold: Threshold for detecting regime changes.
        history_length: Number of historical alpha values to retain.
    """

    def __init__(
        self,
        window_size: int = 150,
        polynomial_order: int = 2,
        ewma_lambda_slow: float = 0.05,
        ewma_lambda_fast: float = 0.3,
        regime_change_threshold: float = 0.1,
        history_length: int = 100,
    ):
        self.window_size = window_size
        self.ewma_lambda_slow = ewma_lambda_slow
        self.ewma_lambda_fast = ewma_lambda_fast
        self.regime_change_threshold = regime_change_threshold
        self.history_length = history_length

        # Initialize DFA calculator
        self.calculator = DFACalculator(
            polynomial_order=polynomial_order,
            min_segment_size=4,
            max_segment_ratio=0.25,
            num_segments=15,  # Fewer segments for rolling calculation efficiency
        )

        # State
        self._ewma_alpha: Optional[float] = None
        self._alpha_history: Deque[AlphaHistoryEntry] = deque(maxlen=history_length)
        self._price_buffer: Deque[float] = deque(maxlen=window_size + 10)
        self._last_result: Optional[DFAResult] = None

    def reset(self):
        """Reset the rolling DFA state."""
        self._ewma_alpha = None
        self._alpha_history.clear()
        self._price_buffer.clear()
        self._last_result = None

    def update(self, prices: np.ndarray, timestamp: Optional[datetime] = None) -> RollingDFAState:
        """
        Update with new price data and return the current DFA state.

        This method can be called with the full price history or just new prices.
        It will use the most recent `window_size` prices for DFA calculation.

        Args:
            prices: Array of prices (most recent should be last).
            timestamp: Optional timestamp for the update.

        Returns:
            RollingDFAState with current alpha values and diagnostics.
        """
        prices = np.asarray(prices, dtype=np.float64)
        timestamp = timestamp or datetime.now()

        # Use the most recent window_size prices
        if len(prices) < self.window_size:
            # If we don't have enough data, use what we have
            window_prices = prices
        else:
            window_prices = prices[-self.window_size:]

        # Calculate DFA
        try:
            result = self.calculator.calculate(window_prices)
            self._last_result = result
        except ValueError:
            # Not enough data or calculation failed
            if self._ewma_alpha is not None:
                # Return last known state
                return RollingDFAState(
                    current_alpha=self._ewma_alpha,
                    ewma_alpha=self._ewma_alpha,
                    r_squared=0.0,
                    alpha_history=[e.alpha for e in self._alpha_history],
                    alpha_std=self._calculate_alpha_std(),
                    last_update=timestamp,
                )
            else:
                # No previous state, return random walk assumption
                return RollingDFAState(
                    current_alpha=0.5,
                    ewma_alpha=0.5,
                    r_squared=0.0,
                    alpha_history=[],
                    alpha_std=0.0,
                    last_update=timestamp,
                )

        raw_alpha = result.alpha

        # Apply EWMA smoothing with adaptive lambda
        if self._ewma_alpha is None:
            # First calculation, no smoothing
            self._ewma_alpha = raw_alpha
        else:
            # Calculate alpha change
            alpha_change = abs(raw_alpha - self._ewma_alpha)

            # Select lambda based on change magnitude
            if alpha_change > self.regime_change_threshold:
                lambda_val = self.ewma_lambda_fast
            else:
                lambda_val = self.ewma_lambda_slow

            # EWMA update: α_smoothed = λ * α_raw + (1 - λ) * α_smoothed_prev
            self._ewma_alpha = lambda_val * raw_alpha + (1 - lambda_val) * self._ewma_alpha

        # Record history
        entry = AlphaHistoryEntry(
            timestamp=timestamp,
            alpha=raw_alpha,
            r_squared=result.r_squared,
            ewma_alpha=self._ewma_alpha,
        )
        self._alpha_history.append(entry)

        return RollingDFAState(
            current_alpha=raw_alpha,
            ewma_alpha=self._ewma_alpha,
            r_squared=result.r_squared,
            alpha_history=[e.alpha for e in self._alpha_history],
            alpha_std=self._calculate_alpha_std(),
            last_update=timestamp,
        )

    def _calculate_alpha_std(self, window: int = 20) -> float:
        """Calculate standard deviation of recent alpha values."""
        if len(self._alpha_history) < 2:
            return 0.0

        recent = list(self._alpha_history)[-window:]
        alphas = [e.alpha for e in recent]
        return float(np.std(alphas))

    def get_state(self) -> Optional[RollingDFAState]:
        """Get the current state without updating."""
        if self._ewma_alpha is None:
            return None

        return RollingDFAState(
            current_alpha=self._last_result.alpha if self._last_result else self._ewma_alpha,
            ewma_alpha=self._ewma_alpha,
            r_squared=self._last_result.r_squared if self._last_result else 0.0,
            alpha_history=[e.alpha for e in self._alpha_history],
            alpha_std=self._calculate_alpha_std(),
            last_update=self._alpha_history[-1].timestamp if self._alpha_history else None,
        )

    def get_history(self) -> List[AlphaHistoryEntry]:
        """Get the full alpha history."""
        return list(self._alpha_history)

    def calculate_full_history(
        self,
        prices: np.ndarray,
        timestamps: Optional[List[datetime]] = None,
    ) -> List[RollingDFAState]:
        """
        Calculate DFA for every point where we have enough data.

        This is useful for backtesting and visualizing how alpha evolves
        over time.

        Args:
            prices: Full price history.
            timestamps: Optional timestamps for each price.

        Returns:
            List of RollingDFAState for each calculation point.
        """
        self.reset()
        prices = np.asarray(prices, dtype=np.float64)

        if timestamps is None:
            timestamps = [datetime.now() for _ in range(len(prices))]

        results = []

        # We need at least window_size prices before we can calculate
        for i in range(self.window_size, len(prices) + 1):
            window_prices = prices[:i]
            timestamp = timestamps[i - 1] if i <= len(timestamps) else datetime.now()

            state = self.update(window_prices, timestamp)
            results.append(state)

        return results

    @property
    def is_initialized(self) -> bool:
        """Check if the rolling DFA has been initialized with data."""
        return self._ewma_alpha is not None

    @property
    def current_alpha(self) -> Optional[float]:
        """Get the current EWMA-smoothed alpha value."""
        return self._ewma_alpha

    @property
    def last_result(self) -> Optional[DFAResult]:
        """Get the most recent full DFA result."""
        return self._last_result
