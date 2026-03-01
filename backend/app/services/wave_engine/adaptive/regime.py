"""
Market regime detection and tracking.

Classifies the market into regimes based on the DFA alpha exponent:
- Trending (α > trending_threshold)
- Mean-reverting (α < mean_reverting_threshold)
- Random walk / Neutral (otherwise)

Also tracks regime changes as events for later analysis.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
from enum import Enum
import numpy as np


class RegimeType(str, Enum):
    """Market regime classification based on DFA alpha."""

    TRENDING = "trending"
    """Strong positive autocorrelation. Movements tend to persist."""

    MEAN_REVERTING = "mean_reverting"
    """Negative autocorrelation. Movements tend to reverse."""

    RANDOM_WALK = "random_walk"
    """No significant autocorrelation. Unpredictable."""


@dataclass
class RegimeChangeEvent:
    """Records a regime change."""

    timestamp: datetime
    """When the regime change occurred."""

    from_regime: RegimeType
    """Previous regime."""

    to_regime: RegimeType
    """New regime."""

    from_alpha: float
    """Alpha value before the change."""

    to_alpha: float
    """Alpha value after the change."""

    confidence: float
    """Confidence in the regime change (0-1)."""

    @property
    def direction(self) -> str:
        """Direction of the regime change."""
        regime_order = {
            RegimeType.MEAN_REVERTING: 0,
            RegimeType.RANDOM_WALK: 1,
            RegimeType.TRENDING: 2,
        }
        if regime_order[self.to_regime] > regime_order[self.from_regime]:
            return "toward_trending"
        elif regime_order[self.to_regime] < regime_order[self.from_regime]:
            return "toward_mean_reverting"
        return "stable"

    @property
    def magnitude(self) -> float:
        """Magnitude of the alpha change."""
        return abs(self.to_alpha - self.from_alpha)


@dataclass
class RegimeState:
    """Current state of market regime detection."""

    current_regime: RegimeType
    """Current regime classification."""

    current_alpha: float
    """Most recent raw alpha value."""

    ewma_alpha: float
    """EWMA-smoothed alpha value (used for classification)."""

    regime_duration_bars: int
    """Number of bars since last regime change."""

    regime_start: Optional[datetime] = None
    """Timestamp when current regime started."""

    alpha_history: List[float] = field(default_factory=list)
    """Recent alpha history for analysis."""

    regime_events: List[RegimeChangeEvent] = field(default_factory=list)
    """History of regime changes."""

    @property
    def is_stable(self) -> bool:
        """Check if the regime has been stable (>10 bars)."""
        return self.regime_duration_bars > 10

    @property
    def regime_strength(self) -> str:
        """Categorize the strength of the current regime."""
        if self.current_regime == RegimeType.TRENDING:
            if self.ewma_alpha > 0.75:
                return "strong"
            return "moderate"
        elif self.current_regime == RegimeType.MEAN_REVERTING:
            if self.ewma_alpha < 0.25:
                return "strong"
            return "moderate"
        return "neutral"

    @property
    def stability_score(self) -> float:
        """
        Score indicating regime stability (0-1).

        Based on:
        - Duration in current regime
        - Variance of recent alpha values
        """
        if len(self.alpha_history) < 5:
            return 0.5

        # Duration component (saturates at 20 bars)
        duration_score = min(1.0, self.regime_duration_bars / 20)

        # Variance component (lower variance = higher score)
        recent_alpha = self.alpha_history[-20:] if len(self.alpha_history) >= 20 else self.alpha_history
        variance = np.var(recent_alpha)
        variance_score = 1.0 / (1.0 + variance * 100)

        return 0.6 * duration_score + 0.4 * variance_score


class RegimeDetector:
    """
    Detects and tracks market regime based on DFA alpha.

    Uses EWMA smoothing with adaptive lambda to smooth alpha values
    and detect regime changes. The adaptive lambda allows quick
    response to genuine regime changes while filtering noise.

    Args:
        trending_threshold: Alpha above which market is trending.
        mean_reverting_threshold: Alpha below which market is mean-reverting.
        ewma_lambda_slow: Smoothing factor for stable conditions.
        ewma_lambda_fast: Smoothing factor for regime transitions.
        regime_change_threshold: Alpha change to trigger fast smoothing.
        min_regime_duration: Minimum bars before regime can change.
    """

    def __init__(
        self,
        trending_threshold: float = 0.65,
        mean_reverting_threshold: float = 0.35,
        ewma_lambda_slow: float = 0.05,
        ewma_lambda_fast: float = 0.3,
        regime_change_threshold: float = 0.1,
        min_regime_duration: int = 3,
    ):
        self.trending_threshold = trending_threshold
        self.mean_reverting_threshold = mean_reverting_threshold
        self.ewma_lambda_slow = ewma_lambda_slow
        self.ewma_lambda_fast = ewma_lambda_fast
        self.regime_change_threshold = regime_change_threshold
        self.min_regime_duration = min_regime_duration

        # State
        self._ewma_alpha: Optional[float] = None
        self._current_regime: Optional[RegimeType] = None
        self._regime_duration: int = 0
        self._regime_start: Optional[datetime] = None
        self._alpha_history: List[float] = []
        self._regime_events: List[RegimeChangeEvent] = []

    def reset(self):
        """Reset the detector state."""
        self._ewma_alpha = None
        self._current_regime = None
        self._regime_duration = 0
        self._regime_start = None
        self._alpha_history = []
        self._regime_events = []

    def update(
        self,
        alpha: float,
        timestamp: Optional[datetime] = None,
    ) -> RegimeState:
        """
        Update regime detection with new alpha value.

        Args:
            alpha: New DFA alpha value.
            timestamp: Optional timestamp for the update.

        Returns:
            Current RegimeState after the update.
        """
        timestamp = timestamp or datetime.now()

        # Initialize on first call
        if self._ewma_alpha is None:
            self._ewma_alpha = alpha
            self._current_regime = self._classify_regime(alpha)
            self._regime_start = timestamp
            self._regime_duration = 1
            self._alpha_history = [alpha]

            return self._get_state()

        # Calculate adaptive lambda
        alpha_change = abs(alpha - self._ewma_alpha)
        if alpha_change > self.regime_change_threshold:
            lambda_val = self.ewma_lambda_fast
        else:
            lambda_val = self.ewma_lambda_slow

        # Update EWMA
        prev_ewma = self._ewma_alpha
        self._ewma_alpha = lambda_val * alpha + (1 - lambda_val) * self._ewma_alpha

        # Update history
        self._alpha_history.append(alpha)
        if len(self._alpha_history) > 100:
            self._alpha_history = self._alpha_history[-100:]

        # Check for regime change
        new_regime = self._classify_regime(self._ewma_alpha)

        if new_regime != self._current_regime:
            # Only change regime if minimum duration met
            if self._regime_duration >= self.min_regime_duration:
                # Record the regime change event
                confidence = self._calculate_change_confidence(prev_ewma, self._ewma_alpha)
                event = RegimeChangeEvent(
                    timestamp=timestamp,
                    from_regime=self._current_regime,
                    to_regime=new_regime,
                    from_alpha=prev_ewma,
                    to_alpha=self._ewma_alpha,
                    confidence=confidence,
                )
                self._regime_events.append(event)

                # Update regime
                self._current_regime = new_regime
                self._regime_duration = 1
                self._regime_start = timestamp
            else:
                self._regime_duration += 1
        else:
            self._regime_duration += 1

        return self._get_state()

    def _classify_regime(self, alpha: float) -> RegimeType:
        """Classify regime based on alpha value."""
        if alpha > self.trending_threshold:
            return RegimeType.TRENDING
        elif alpha < self.mean_reverting_threshold:
            return RegimeType.MEAN_REVERTING
        return RegimeType.RANDOM_WALK

    def _calculate_change_confidence(self, prev_alpha: float, new_alpha: float) -> float:
        """
        Calculate confidence in a regime change.

        Based on:
        - Magnitude of alpha change
        - Clarity of crossing threshold
        - Variance of recent alpha values
        """
        # Magnitude component
        change_magnitude = abs(new_alpha - prev_alpha)
        magnitude_score = min(1.0, change_magnitude / 0.2)

        # Threshold crossing clarity
        # How far into the new regime are we?
        if new_alpha > self.trending_threshold:
            clarity = (new_alpha - self.trending_threshold) / 0.15
        elif new_alpha < self.mean_reverting_threshold:
            clarity = (self.mean_reverting_threshold - new_alpha) / 0.15
        else:
            clarity = 0.5

        clarity_score = min(1.0, max(0.0, clarity))

        # Variance component
        if len(self._alpha_history) >= 5:
            variance = np.var(self._alpha_history[-10:])
            variance_score = 1.0 / (1.0 + variance * 50)
        else:
            variance_score = 0.5

        return 0.4 * magnitude_score + 0.4 * clarity_score + 0.2 * variance_score

    def _get_state(self) -> RegimeState:
        """Get current regime state."""
        return RegimeState(
            current_regime=self._current_regime or RegimeType.RANDOM_WALK,
            current_alpha=self._alpha_history[-1] if self._alpha_history else 0.5,
            ewma_alpha=self._ewma_alpha or 0.5,
            regime_duration_bars=self._regime_duration,
            regime_start=self._regime_start,
            alpha_history=list(self._alpha_history),
            regime_events=list(self._regime_events),
        )

    def get_state(self) -> Optional[RegimeState]:
        """Get current state without updating."""
        if self._ewma_alpha is None:
            return None
        return self._get_state()

    def get_regime_events(self) -> List[RegimeChangeEvent]:
        """Get all recorded regime change events."""
        return list(self._regime_events)

    @property
    def is_initialized(self) -> bool:
        """Check if the detector has been initialized."""
        return self._ewma_alpha is not None

    @property
    def current_regime(self) -> Optional[RegimeType]:
        """Get current regime classification."""
        return self._current_regime
