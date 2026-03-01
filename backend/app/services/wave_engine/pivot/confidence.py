"""
Confidence scoring for pivots.

Calculates confidence scores based on multiple components:
- k1: Threshold distance (how far amplitude exceeds threshold)
- k2: Timeframe consistency (confirmed on multiple timeframes)
- k3: DFA stability (how stable alpha was during pivot formation)
- k4: Structural validity (fits expected structure)

confidence = w1*k1 + w2*k2 + w3*k3 + w4*k4
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np

from .detector import EnhancedPivot, PivotType


@dataclass
class ConfidenceComponents:
    """Individual confidence components for a pivot."""

    k1_threshold_distance: float
    """How far amplitude exceeds the threshold (0-1)."""

    k2_timeframe_consistency: float
    """Proportion of timeframes where this pivot exists (0-1)."""

    k3_dfa_stability: float
    """Stability of DFA alpha during pivot formation (0-1)."""

    k4_structural_validity: float
    """Whether the pivot fits the local structure (0-1)."""

    @property
    def total(self) -> float:
        """Sum of all components (unweighted)."""
        return (
            self.k1_threshold_distance +
            self.k2_timeframe_consistency +
            self.k3_dfa_stability +
            self.k4_structural_validity
        )


class ConfidenceCalculator:
    """
    Calculates confidence scores for pivots.

    The confidence score aggregates multiple factors to give a single
    number between 0 and 100 indicating how reliable a pivot is.

    Args:
        w1: Weight for threshold distance component.
        w2: Weight for timeframe consistency component.
        w3: Weight for DFA stability component.
        w4: Weight for structural validity component.
    """

    def __init__(
        self,
        w1: float = 0.30,
        w2: float = 0.35,
        w3: float = 0.15,
        w4: float = 0.20,
    ):
        self.w1 = w1
        self.w2 = w2
        self.w3 = w3
        self.w4 = w4

        # Normalize weights
        total = w1 + w2 + w3 + w4
        self.w1 /= total
        self.w2 /= total
        self.w3 /= total
        self.w4 /= total

    def calculate(
        self,
        pivot: EnhancedPivot,
        tau: float,
        alpha_history: List[float],
        timeframe_confirmations: int,
        total_timeframes: int,
        previous_pivot: Optional[EnhancedPivot] = None,
        next_pivot: Optional[EnhancedPivot] = None,
    ) -> Tuple[float, ConfidenceComponents]:
        """
        Calculate confidence score for a pivot.

        Args:
            pivot: The pivot to score.
            tau: Current adaptive threshold.
            alpha_history: Recent DFA alpha values.
            timeframe_confirmations: Number of timeframes confirming this pivot.
            total_timeframes: Total number of active timeframes.
            previous_pivot: Previous pivot in sequence (for structure check).
            next_pivot: Next pivot in sequence (for structure check).

        Returns:
            Tuple of (overall_confidence, ConfidenceComponents).
        """
        # K1: Threshold distance
        k1 = self._calculate_k1(pivot.amplitude, tau)

        # K2: Timeframe consistency
        k2 = self._calculate_k2(timeframe_confirmations, total_timeframes)

        # K3: DFA stability
        k3 = self._calculate_k3(alpha_history)

        # K4: Structural validity
        k4 = self._calculate_k4(pivot, previous_pivot, next_pivot)

        components = ConfidenceComponents(
            k1_threshold_distance=k1,
            k2_timeframe_consistency=k2,
            k3_dfa_stability=k3,
            k4_structural_validity=k4,
        )

        # Calculate weighted sum
        confidence = (
            self.w1 * k1 +
            self.w2 * k2 +
            self.w3 * k3 +
            self.w4 * k4
        ) * 100  # Scale to 0-100

        return confidence, components

    def _calculate_k1(self, amplitude: float, tau: float) -> float:
        """
        Calculate threshold distance component.

        k1 = min(1.0, (amplitude - τ) / τ)

        When amplitude = τ: k1 = 0 (barely above threshold)
        When amplitude = 2τ: k1 = 1 (significantly above threshold)
        """
        if tau <= 0:
            return 0.5

        excess = amplitude - tau
        if excess <= 0:
            return 0.0

        return min(1.0, excess / tau)

    def _calculate_k2(self, confirmations: int, total: int) -> float:
        """
        Calculate timeframe consistency component.

        k2 = confirmations / total_timeframes

        A pivot confirmed on multiple timeframes is more reliable.
        """
        if total <= 0:
            return 0.5

        return min(1.0, confirmations / total)

    def _calculate_k3(self, alpha_history: List[float], window: int = 10) -> float:
        """
        Calculate DFA stability component.

        k3 = 1 - min(1, σ_α / 0.1)

        Lower variance in alpha = higher stability = higher confidence.
        """
        if len(alpha_history) < 2:
            return 0.5

        # Use recent window
        recent = alpha_history[-window:] if len(alpha_history) >= window else alpha_history
        std_alpha = np.std(recent)

        # Scale: std of 0.1 or higher gives k3 = 0
        return max(0.0, 1.0 - std_alpha / 0.1)

    def _calculate_k4(
        self,
        pivot: EnhancedPivot,
        previous_pivot: Optional[EnhancedPivot],
        next_pivot: Optional[EnhancedPivot],
    ) -> float:
        """
        Calculate structural validity component.

        Checks:
        1. Previous pivot is opposite type
        2. No overlapping extremes between same-type pivots

        k4 = 1.0 if both conditions met
        k4 = 0.5 if one condition violated
        k4 = 0.0 if both conditions violated
        """
        score = 1.0
        violations = 0

        # Check 1: Previous pivot should be opposite type
        if previous_pivot is not None:
            if previous_pivot.type == pivot.type:
                violations += 1

        # Check 2: For highs, no higher high since last high
        # For lows, no lower low since last low
        if previous_pivot is not None and next_pivot is not None:
            if pivot.type == PivotType.HIGH:
                # Check if there's a higher high between this and next same-type
                if next_pivot.type == PivotType.HIGH:
                    if next_pivot.price > pivot.price:
                        violations += 1
            else:  # LOW
                if next_pivot.type == PivotType.LOW:
                    if next_pivot.price < pivot.price:
                        violations += 1

        # Convert violations to score
        if violations == 0:
            return 1.0
        elif violations == 1:
            return 0.5
        else:
            return 0.0

    def update_pivot_confidence(
        self,
        pivot: EnhancedPivot,
        tau: float,
        alpha_history: List[float],
        timeframe_confirmations: int = 1,
        total_timeframes: int = 1,
        previous_pivot: Optional[EnhancedPivot] = None,
        next_pivot: Optional[EnhancedPivot] = None,
    ) -> EnhancedPivot:
        """
        Update a pivot with its confidence score.

        Args:
            pivot: Pivot to update.
            tau: Current threshold.
            alpha_history: Recent alpha values.
            timeframe_confirmations: Number of confirming timeframes.
            total_timeframes: Total active timeframes.
            previous_pivot: Previous pivot in sequence.
            next_pivot: Next pivot in sequence.

        Returns:
            Updated pivot with confidence scores.
        """
        confidence, components = self.calculate(
            pivot=pivot,
            tau=tau,
            alpha_history=alpha_history,
            timeframe_confirmations=timeframe_confirmations,
            total_timeframes=total_timeframes,
            previous_pivot=previous_pivot,
            next_pivot=next_pivot,
        )

        pivot.overall_confidence = confidence
        pivot.confidence_components = {
            "k1_threshold_distance": components.k1_threshold_distance,
            "k2_timeframe_consistency": components.k2_timeframe_consistency,
            "k3_dfa_stability": components.k3_dfa_stability,
            "k4_structural_validity": components.k4_structural_validity,
        }

        return pivot

    def batch_update_confidence(
        self,
        pivots: List[EnhancedPivot],
        tau: float,
        alpha_history: List[float],
        timeframe_confirmations: int = 1,
        total_timeframes: int = 1,
    ) -> List[EnhancedPivot]:
        """
        Update confidence for a list of pivots.

        Args:
            pivots: List of pivots to update.
            tau: Current threshold.
            alpha_history: Recent alpha values.
            timeframe_confirmations: Number of confirming timeframes.
            total_timeframes: Total active timeframes.

        Returns:
            List of pivots with updated confidence scores.
        """
        for i, pivot in enumerate(pivots):
            prev_pivot = pivots[i - 1] if i > 0 else None
            next_pivot = pivots[i + 1] if i < len(pivots) - 1 else None

            self.update_pivot_confidence(
                pivot=pivot,
                tau=tau,
                alpha_history=alpha_history,
                timeframe_confirmations=timeframe_confirmations,
                total_timeframes=total_timeframes,
                previous_pivot=prev_pivot,
                next_pivot=next_pivot,
            )

        return pivots

    @staticmethod
    def confidence_category(confidence: float) -> str:
        """
        Convert confidence score to human-readable category.

        Args:
            confidence: Score from 0-100.

        Returns:
            Category string for UI display.
        """
        if confidence >= 80:
            return "very_high"
        elif confidence >= 60:
            return "high"
        elif confidence >= 40:
            return "medium"
        elif confidence >= 20:
            return "low"
        else:
            return "very_low"
