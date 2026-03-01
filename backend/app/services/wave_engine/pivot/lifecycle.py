"""
Pivot lifecycle management.

Manages the state transitions of pivots through their lifecycle:
POTENTIAL → CONFIRMED → PROMOTED → (INVALID)

A pivot can be invalidated at any stage if subsequent price action
contradicts its validity.
"""

from typing import List, Optional
from datetime import datetime
import numpy as np

from .detector import EnhancedPivot, PivotStatus, PivotType


class PivotLifecycleManager:
    """
    Manages pivot lifecycle transitions.

    Handles:
    - Confirmation of potential pivots
    - Promotion to higher timeframes
    - Invalidation based on price action

    Args:
        confirmation_bars: Bars required to confirm a potential pivot.
        invalidation_margin: Extra margin beyond pivot price for invalidation.
    """

    def __init__(
        self,
        confirmation_bars: int = 2,
        invalidation_margin: float = 0.001,  # 0.1% margin
    ):
        self.confirmation_bars = confirmation_bars
        self.invalidation_margin = invalidation_margin

    def update_status(
        self,
        pivots: List[EnhancedPivot],
        current_high: float,
        current_low: float,
        current_index: int,
    ) -> List[EnhancedPivot]:
        """
        Update status of all pivots based on current price action.

        Args:
            pivots: List of pivots to update.
            current_high: Current bar's high price.
            current_low: Current bar's low price.
            current_index: Current bar index.

        Returns:
            Updated list of pivots.
        """
        for pivot in pivots:
            if pivot.status == PivotStatus.INVALID:
                continue

            # Check for invalidation
            if self._should_invalidate(pivot, current_high, current_low):
                pivot.status = PivotStatus.INVALID
                continue

            # Check for confirmation of potential pivots
            if pivot.status == PivotStatus.POTENTIAL:
                bars_since = current_index - pivot.index
                if bars_since >= self.confirmation_bars:
                    if self._can_confirm(pivot, current_high, current_low):
                        pivot.status = PivotStatus.CONFIRMED

        return pivots

    def _should_invalidate(
        self,
        pivot: EnhancedPivot,
        current_high: float,
        current_low: float,
    ) -> bool:
        """
        Check if a pivot should be invalidated.

        A high pivot is invalidated if price makes a higher high.
        A low pivot is invalidated if price makes a lower low.
        """
        margin = pivot.price * self.invalidation_margin

        if pivot.type == PivotType.HIGH:
            return current_high > pivot.price + margin
        else:  # LOW
            return current_low < pivot.price - margin

    def _can_confirm(
        self,
        pivot: EnhancedPivot,
        current_high: float,
        current_low: float,
    ) -> bool:
        """
        Check if a potential pivot can be confirmed.

        A high pivot is confirmed if price has moved down from it.
        A low pivot is confirmed if price has moved up from it.
        """
        # Use the threshold at creation as a reference
        tau = pivot.tau_at_creation

        if pivot.type == PivotType.HIGH:
            return current_low < pivot.price - tau * 0.5
        else:  # LOW
            return current_high > pivot.price + tau * 0.5

    def promote_pivot(
        self,
        pivot: EnhancedPivot,
        higher_timeframe: str,
        parent_id: Optional[str] = None,
    ) -> EnhancedPivot:
        """
        Promote a pivot to a higher timeframe.

        Args:
            pivot: Pivot to promote.
            higher_timeframe: Target timeframe.
            parent_id: ID of corresponding pivot on higher timeframe.

        Returns:
            Updated pivot with PROMOTED status.
        """
        pivot.status = PivotStatus.PROMOTED
        pivot.parent_pivot_id = parent_id
        return pivot

    def check_promotion_eligibility(
        self,
        pivot: EnhancedPivot,
        higher_tau: float,
    ) -> bool:
        """
        Check if a pivot is eligible for promotion to a higher timeframe.

        Criteria:
        - Pivot must be confirmed
        - Amplitude must exceed the higher timeframe's threshold

        Args:
            pivot: Pivot to check.
            higher_tau: Threshold of the higher timeframe.

        Returns:
            True if eligible for promotion.
        """
        if pivot.status != PivotStatus.CONFIRMED:
            return False

        return pivot.amplitude >= higher_tau

    def find_invalidations(
        self,
        pivots: List[EnhancedPivot],
        highs: np.ndarray,
        lows: np.ndarray,
        from_index: int,
    ) -> List[int]:
        """
        Find indices where pivots get invalidated.

        Useful for backtesting to understand when pivots were invalidated.

        Args:
            pivots: List of pivots to check.
            highs: Array of high prices.
            lows: Array of low prices.
            from_index: Starting index for checking.

        Returns:
            List of invalidation indices for each pivot (-1 if not invalidated).
        """
        invalidation_indices = []

        for pivot in pivots:
            found = False
            for i in range(max(from_index, pivot.index + 1), len(highs)):
                if self._should_invalidate(pivot, highs[i], lows[i]):
                    invalidation_indices.append(i)
                    found = True
                    break

            if not found:
                invalidation_indices.append(-1)

        return invalidation_indices

    def get_valid_sequence(
        self,
        pivots: List[EnhancedPivot],
    ) -> List[EnhancedPivot]:
        """
        Get a valid alternating sequence of pivots.

        Ensures the sequence alternates between HIGH and LOW pivots,
        removing any that violate this constraint.

        Args:
            pivots: List of pivots (may have invalid or non-alternating).

        Returns:
            Cleaned list of alternating valid pivots.
        """
        valid = [p for p in pivots if p.is_valid]

        if len(valid) <= 1:
            return valid

        # Sort by index
        valid = sorted(valid, key=lambda p: p.index)

        # Ensure alternation
        result = [valid[0]]
        for pivot in valid[1:]:
            if pivot.type != result[-1].type:
                result.append(pivot)
            else:
                # Same type - keep the more extreme one
                if pivot.type == PivotType.HIGH:
                    if pivot.price > result[-1].price:
                        result[-1] = pivot
                else:
                    if pivot.price < result[-1].price:
                        result[-1] = pivot

        return result
