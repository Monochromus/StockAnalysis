"""
Adaptive threshold calculation.

Combines ATR (Average True Range) with the DFA-based sigmoid mapping
to produce a threshold that adapts to current market conditions.

τ = ATR(period) × f(α)

where:
- ATR measures current volatility
- f(α) adjusts sensitivity based on market regime (from sigmoid mapping)
"""

from dataclasses import dataclass
from typing import List, Optional
import numpy as np

from .sigmoid import SigmoidMapper


@dataclass
class ThresholdResult:
    """Result of adaptive threshold calculation."""

    tau: float
    """The adaptive threshold value (in price units)."""

    atr: float
    """The ATR value used."""

    multiplier: float
    """The sigmoid multiplier f(α) applied to ATR."""

    alpha: float
    """The DFA alpha value used for the calculation."""

    tau_percent: float
    """Threshold as percentage of current price."""

    @property
    def explanation(self) -> str:
        """Human-readable explanation of the threshold."""
        if self.multiplier < 1.0:
            sensitivity = "high"
            reason = "mean-reverting market conditions"
        elif self.multiplier < 2.0:
            sensitivity = "moderate"
            reason = "neutral market conditions"
        else:
            sensitivity = "low"
            reason = "trending market conditions"

        return (
            f"Threshold τ = {self.tau:.4f} ({self.tau_percent:.2f}% of price)\n"
            f"Sensitivity: {sensitivity} (multiplier: {self.multiplier:.2f}x ATR)\n"
            f"Based on: ATR({self.atr:.4f}) × {self.multiplier:.2f} due to {reason} (α={self.alpha:.3f})"
        )


class AdaptiveThreshold:
    """
    Calculates adaptive threshold based on ATR and DFA alpha.

    The threshold adapts to:
    1. Current volatility (via ATR)
    2. Market regime (via DFA alpha through sigmoid mapping)

    In trending markets (high α), the threshold is larger to avoid
    whipsaws from noise. In mean-reverting markets (low α), the
    threshold is smaller to capture the smaller, more frequent swings.

    Args:
        atr_period: Period for ATR calculation.
        beta_min: Minimum sigmoid multiplier.
        beta_max: Maximum sigmoid multiplier.
        sigmoid_k: Steepness of sigmoid.
        alpha_mid: Midpoint of sigmoid.
    """

    def __init__(
        self,
        atr_period: int = 14,
        beta_min: float = 0.5,
        beta_max: float = 3.0,
        sigmoid_k: float = 10.0,
        alpha_mid: float = 0.5,
    ):
        self.atr_period = atr_period
        self.sigmoid_mapper = SigmoidMapper(
            beta_min=beta_min,
            beta_max=beta_max,
            k=sigmoid_k,
            alpha_mid=alpha_mid,
        )

    def calculate(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        alpha: float,
        current_price: Optional[float] = None,
    ) -> ThresholdResult:
        """
        Calculate the adaptive threshold.

        Args:
            highs: Array of high prices.
            lows: Array of low prices.
            closes: Array of close prices.
            alpha: Current DFA alpha value.
            current_price: Current price for percentage calculation.
                          If None, uses last close.

        Returns:
            ThresholdResult with the calculated threshold and diagnostics.
        """
        # Calculate ATR
        atr = self._calculate_atr(highs, lows, closes)

        # Map alpha to multiplier
        multiplier = self.sigmoid_mapper.map(alpha)

        # Calculate threshold
        tau = atr * multiplier

        # Calculate percentage
        if current_price is None:
            current_price = closes[-1]
        tau_percent = (tau / current_price) * 100 if current_price > 0 else 0

        return ThresholdResult(
            tau=tau,
            atr=atr,
            multiplier=multiplier,
            alpha=alpha,
            tau_percent=tau_percent,
        )

    def _calculate_atr(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
    ) -> float:
        """
        Calculate Average True Range.

        True Range is the maximum of:
        - Current High - Current Low
        - |Current High - Previous Close|
        - |Current Low - Previous Close|
        """
        highs = np.asarray(highs, dtype=np.float64)
        lows = np.asarray(lows, dtype=np.float64)
        closes = np.asarray(closes, dtype=np.float64)

        if len(highs) < 2:
            return highs[0] - lows[0] if len(highs) > 0 else 0.0

        # Calculate True Range components
        high_low = highs[1:] - lows[1:]
        high_prev_close = np.abs(highs[1:] - closes[:-1])
        low_prev_close = np.abs(lows[1:] - closes[:-1])

        # True Range is the maximum of the three
        true_range = np.maximum(high_low, np.maximum(high_prev_close, low_prev_close))

        # Take the average over the period
        if len(true_range) < self.atr_period:
            return float(np.mean(true_range))

        # Use EMA-style ATR for the most recent period
        return float(np.mean(true_range[-self.atr_period:]))

    def calculate_from_candles(
        self,
        candles: List[dict],
        alpha: float,
    ) -> ThresholdResult:
        """
        Calculate threshold from candle data.

        Args:
            candles: List of candle dicts with 'high', 'low', 'close' keys.
            alpha: Current DFA alpha value.

        Returns:
            ThresholdResult with the calculated threshold.
        """
        highs = np.array([c["high"] for c in candles])
        lows = np.array([c["low"] for c in candles])
        closes = np.array([c["close"] for c in candles])

        return self.calculate(highs, lows, closes, alpha)

    def get_threshold_range(self, atr: float) -> tuple:
        """
        Get the range of possible thresholds for a given ATR.

        Useful for understanding the sensitivity range.

        Args:
            atr: ATR value.

        Returns:
            Tuple of (min_threshold, max_threshold).
        """
        min_tau = atr * self.sigmoid_mapper.beta_min
        max_tau = atr * self.sigmoid_mapper.beta_max
        return min_tau, max_tau

    def alpha_for_threshold(self, tau: float, atr: float) -> float:
        """
        Find the alpha that would produce a given threshold.

        Useful for backtesting and understanding what regime
        would result in a particular threshold level.

        Args:
            tau: Desired threshold.
            atr: Current ATR.

        Returns:
            Alpha value that would produce this threshold.
        """
        multiplier = tau / atr if atr > 0 else 1.0
        return self.sigmoid_mapper.inverse(multiplier)
