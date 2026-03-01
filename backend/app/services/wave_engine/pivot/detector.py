"""
Adaptive pivot detection using DFA-based thresholds.

This module replaces the fixed-threshold ZigZag detection with an adaptive
approach that adjusts sensitivity based on market regime.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
from enum import Enum
import uuid
import numpy as np

from ..adaptive.regime import RegimeType


class PivotType(str, Enum):
    """Type of pivot point."""

    HIGH = "high"
    LOW = "low"


class PivotStatus(str, Enum):
    """Status of a pivot in its lifecycle."""

    POTENTIAL = "potential"
    """Newly detected, awaiting confirmation."""

    CONFIRMED = "confirmed"
    """Met confirmation criteria on this timeframe."""

    PROMOTED = "promoted"
    """Propagated to a higher timeframe."""

    INVALID = "invalid"
    """Invalidated by subsequent price action."""


@dataclass
class EnhancedPivot:
    """
    Enhanced pivot with status, confidence, and DFA context.

    Extends the basic pivot concept with:
    - Lifecycle status tracking
    - Confidence scoring
    - DFA/regime context at creation
    - Hierarchy tracking for multi-timeframe analysis
    """

    # Core pivot data
    timestamp: datetime
    """Timestamp of the candle that forms this pivot."""

    price: float
    """Price level of the pivot (high or low of the candle)."""

    type: PivotType
    """Whether this is a swing high or swing low."""

    index: int
    """Index in the candle array."""

    # Calculated metrics
    amplitude: float
    """Price movement that led to this pivot (from previous pivot)."""

    significance: float
    """Significance score as percentage of price movement."""

    # Status tracking
    status: PivotStatus = PivotStatus.POTENTIAL
    """Current lifecycle status."""

    # Confidence
    overall_confidence: float = 0.0
    """Overall confidence score (0-100)."""

    confidence_components: Optional[dict] = None
    """Breakdown of confidence components (k1, k2, k3, k4)."""

    # DFA context at pivot creation
    alpha_at_creation: float = 0.5
    """DFA alpha value when this pivot was detected."""

    tau_at_creation: float = 0.0
    """Adaptive threshold value when this pivot was detected."""

    regime_at_creation: RegimeType = RegimeType.RANDOM_WALK
    """Market regime when this pivot was detected."""

    # Timeframe tracking
    timeframe: str = "1d"
    """Timeframe level where this pivot was detected."""

    # Hierarchy
    pivot_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    """Unique identifier for tracking across timeframes."""

    parent_pivot_id: Optional[str] = None
    """ID of corresponding pivot on higher timeframe (if promoted)."""

    child_pivot_ids: List[str] = field(default_factory=list)
    """IDs of corresponding pivots on lower timeframes."""

    @property
    def is_high(self) -> bool:
        """Check if this is a swing high."""
        return self.type == PivotType.HIGH

    @property
    def is_low(self) -> bool:
        """Check if this is a swing low."""
        return self.type == PivotType.LOW

    @property
    def is_valid(self) -> bool:
        """Check if the pivot is still valid (not invalidated)."""
        return self.status != PivotStatus.INVALID

    @property
    def is_confirmed(self) -> bool:
        """Check if the pivot has been confirmed."""
        return self.status in (PivotStatus.CONFIRMED, PivotStatus.PROMOTED)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "price": self.price,
            "type": self.type.value,
            "index": self.index,
            "amplitude": self.amplitude,
            "significance": self.significance,
            "status": self.status.value,
            "overall_confidence": self.overall_confidence,
            "confidence_components": self.confidence_components,
            "alpha_at_creation": self.alpha_at_creation,
            "tau_at_creation": self.tau_at_creation,
            "regime_at_creation": self.regime_at_creation.value,
            "timeframe": self.timeframe,
            "pivot_id": self.pivot_id,
            "parent_pivot_id": self.parent_pivot_id,
            "child_pivot_ids": self.child_pivot_ids,
        }


@dataclass
class EnhancedPivotSequence:
    """Sequence of enhanced pivots with metadata."""

    pivots: List[EnhancedPivot]
    """List of detected pivots."""

    timeframe: str
    """Timeframe of this sequence."""

    current_tau: float
    """Current adaptive threshold."""

    current_alpha: float
    """Current DFA alpha."""

    current_regime: RegimeType
    """Current market regime."""

    total_candles: int
    """Total number of candles analyzed."""

    @property
    def valid_pivots(self) -> List[EnhancedPivot]:
        """Get only valid (non-invalidated) pivots."""
        return [p for p in self.pivots if p.is_valid]

    @property
    def confirmed_pivots(self) -> List[EnhancedPivot]:
        """Get only confirmed pivots."""
        return [p for p in self.pivots if p.is_confirmed]

    @property
    def high_pivots(self) -> List[EnhancedPivot]:
        """Get only swing highs."""
        return [p for p in self.pivots if p.is_high and p.is_valid]

    @property
    def low_pivots(self) -> List[EnhancedPivot]:
        """Get only swing lows."""
        return [p for p in self.pivots if p.is_low and p.is_valid]


class AdaptivePivotDetector:
    """
    Detects pivot points using adaptive thresholds.

    Instead of a fixed percentage threshold, uses:
    τ = ATR × f(α)

    where the threshold adapts to:
    - Current volatility (ATR)
    - Market regime (via DFA alpha)

    Args:
        confirmation_bars: Number of bars required to confirm a pivot.
        min_amplitude_ratio: Minimum amplitude as ratio of threshold.
    """

    def __init__(
        self,
        confirmation_bars: int = 2,
        min_amplitude_ratio: float = 0.5,
    ):
        self.confirmation_bars = confirmation_bars
        self.min_amplitude_ratio = min_amplitude_ratio

    def detect(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        timestamps: List[datetime],
        tau: float,
        alpha: float,
        regime: RegimeType,
        timeframe: str = "1d",
    ) -> EnhancedPivotSequence:
        """
        Detect pivots using the adaptive threshold.

        Args:
            highs: Array of high prices.
            lows: Array of low prices.
            closes: Array of close prices.
            timestamps: List of timestamps.
            tau: Adaptive threshold (in price units).
            alpha: Current DFA alpha.
            regime: Current market regime.
            timeframe: Timeframe identifier.

        Returns:
            EnhancedPivotSequence with detected pivots.
        """
        highs = np.asarray(highs, dtype=np.float64)
        lows = np.asarray(lows, dtype=np.float64)
        closes = np.asarray(closes, dtype=np.float64)

        n = len(highs)
        if n < 3:
            return EnhancedPivotSequence(
                pivots=[],
                timeframe=timeframe,
                current_tau=tau,
                current_alpha=alpha,
                current_regime=regime,
                total_candles=n,
            )

        pivots: List[EnhancedPivot] = []

        # Find initial direction by scanning first few bars
        first_high_idx = 0
        first_low_idx = 0
        first_high = highs[0]
        first_low = lows[0]

        scan_length = min(10, n)
        for i in range(scan_length):
            if highs[i] > first_high:
                first_high = highs[i]
                first_high_idx = i
            if lows[i] < first_low:
                first_low = lows[i]
                first_low_idx = i

        # Determine initial direction
        if first_high_idx < first_low_idx:
            last_pivot_type = PivotType.HIGH
            last_pivot_price = first_high
            last_pivot_idx = first_high_idx
        else:
            last_pivot_type = PivotType.LOW
            last_pivot_price = first_low
            last_pivot_idx = first_low_idx

        # Track potential pivot
        potential_pivot_price = last_pivot_price
        potential_pivot_idx = last_pivot_idx

        for i in range(n):
            if last_pivot_type == PivotType.HIGH:
                # Looking for a low
                if lows[i] < potential_pivot_price:
                    potential_pivot_price = lows[i]
                    potential_pivot_idx = i

                # Check if we've moved enough to confirm the low
                if highs[i] > potential_pivot_price + tau:
                    amplitude = last_pivot_price - potential_pivot_price
                    significance = (amplitude / last_pivot_price) * 100 if last_pivot_price > 0 else 0

                    pivot = EnhancedPivot(
                        timestamp=timestamps[potential_pivot_idx],
                        price=potential_pivot_price,
                        type=PivotType.LOW,
                        index=potential_pivot_idx,
                        amplitude=amplitude,
                        significance=significance,
                        status=PivotStatus.CONFIRMED,
                        alpha_at_creation=alpha,
                        tau_at_creation=tau,
                        regime_at_creation=regime,
                        timeframe=timeframe,
                    )
                    pivots.append(pivot)

                    last_pivot_type = PivotType.LOW
                    last_pivot_price = potential_pivot_price
                    last_pivot_idx = potential_pivot_idx
                    potential_pivot_price = highs[i]
                    potential_pivot_idx = i

            else:  # Looking for a high
                if highs[i] > potential_pivot_price:
                    potential_pivot_price = highs[i]
                    potential_pivot_idx = i

                # Check if we've moved enough to confirm the high
                if lows[i] < potential_pivot_price - tau:
                    amplitude = potential_pivot_price - last_pivot_price
                    significance = (amplitude / last_pivot_price) * 100 if last_pivot_price > 0 else 0

                    pivot = EnhancedPivot(
                        timestamp=timestamps[potential_pivot_idx],
                        price=potential_pivot_price,
                        type=PivotType.HIGH,
                        index=potential_pivot_idx,
                        amplitude=amplitude,
                        significance=significance,
                        status=PivotStatus.CONFIRMED,
                        alpha_at_creation=alpha,
                        tau_at_creation=tau,
                        regime_at_creation=regime,
                        timeframe=timeframe,
                    )
                    pivots.append(pivot)

                    last_pivot_type = PivotType.HIGH
                    last_pivot_price = potential_pivot_price
                    last_pivot_idx = potential_pivot_idx
                    potential_pivot_price = lows[i]
                    potential_pivot_idx = i

        # Add the last potential pivot if significant
        if potential_pivot_idx != last_pivot_idx:
            amplitude = abs(potential_pivot_price - last_pivot_price)
            min_amplitude = tau * self.min_amplitude_ratio

            if amplitude >= min_amplitude:
                final_type = PivotType.LOW if last_pivot_type == PivotType.HIGH else PivotType.HIGH
                significance = (amplitude / last_pivot_price) * 100 if last_pivot_price > 0 else 0

                pivot = EnhancedPivot(
                    timestamp=timestamps[potential_pivot_idx],
                    price=potential_pivot_price,
                    type=final_type,
                    index=potential_pivot_idx,
                    amplitude=amplitude,
                    significance=significance,
                    status=PivotStatus.POTENTIAL,  # Last pivot is always potential
                    alpha_at_creation=alpha,
                    tau_at_creation=tau,
                    regime_at_creation=regime,
                    timeframe=timeframe,
                )
                pivots.append(pivot)

        return EnhancedPivotSequence(
            pivots=pivots,
            timeframe=timeframe,
            current_tau=tau,
            current_alpha=alpha,
            current_regime=regime,
            total_candles=n,
        )

    def detect_from_candles(
        self,
        candles: List[dict],
        tau: float,
        alpha: float,
        regime: RegimeType,
        timeframe: str = "1d",
    ) -> EnhancedPivotSequence:
        """
        Detect pivots from candle dictionaries.

        Args:
            candles: List of candle dicts with 'high', 'low', 'close', 'timestamp'.
            tau: Adaptive threshold.
            alpha: Current DFA alpha.
            regime: Current market regime.
            timeframe: Timeframe identifier.

        Returns:
            EnhancedPivotSequence with detected pivots.
        """
        highs = np.array([c["high"] for c in candles])
        lows = np.array([c["low"] for c in candles])
        closes = np.array([c["close"] for c in candles])
        timestamps = [c["timestamp"] for c in candles]

        return self.detect(highs, lows, closes, timestamps, tau, alpha, regime, timeframe)
