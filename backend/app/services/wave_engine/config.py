"""
Configuration classes for the Wave Engine.

All parameters are user-configurable with sensible defaults.
Each config class includes validation via Pydantic Field constraints.
"""

from dataclasses import dataclass, field
from typing import List
from enum import Enum


class TimeframeLevel(str, Enum):
    """Supported timeframe levels for multi-timeframe analysis."""

    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1wk"


@dataclass
class DFAConfig:
    """
    Configuration for Detrended Fluctuation Analysis.

    Attributes:
        window_size: Number of data points for rolling DFA calculation.
                    Larger windows provide more stable estimates but less responsiveness.
                    Recommended: 100-250 for daily data.
        polynomial_order: Order of polynomial for detrending (1=linear, 2=quadratic, 3=cubic).
                         DFA-2 (quadratic) is recommended for financial data as it removes
                         linear and quadratic trends.
        min_segment_size: Minimum segment size for DFA calculation.
                         Must be at least 4 for meaningful polynomial fitting.
        max_segment_ratio: Maximum segment size as ratio of data length.
                          Ensures enough segments for statistical validity.
    """

    window_size: int = 150
    polynomial_order: int = 2
    min_segment_size: int = 4
    max_segment_ratio: float = 0.25

    def __post_init__(self):
        if not 50 <= self.window_size <= 500:
            raise ValueError(f"window_size must be between 50 and 500, got {self.window_size}")
        if not 1 <= self.polynomial_order <= 3:
            raise ValueError(f"polynomial_order must be 1, 2, or 3, got {self.polynomial_order}")
        if not 2 <= self.min_segment_size <= 10:
            raise ValueError(f"min_segment_size must be between 2 and 10, got {self.min_segment_size}")
        if not 0 < self.max_segment_ratio <= 0.5:
            raise ValueError(f"max_segment_ratio must be between 0 and 0.5, got {self.max_segment_ratio}")


@dataclass
class ThresholdConfig:
    """
    Configuration for adaptive threshold calculation.

    The adaptive threshold τ = ATR(period) × f(α) where f(α) is a sigmoid mapping
    that adjusts sensitivity based on the DFA exponent.

    Attributes:
        atr_period: Period for Average True Range calculation.
        beta_min: Minimum threshold multiplier (for mean-reverting markets, α << 0.5).
                 Lower values mean more sensitivity to smaller swings.
        beta_max: Maximum threshold multiplier (for trending markets, α >> 0.5).
                 Higher values mean less sensitivity, only large swings count.
        sigmoid_k: Steepness of the sigmoid transition. Higher = sharper transition.
        alpha_mid: Midpoint of the sigmoid (where f(α) = (beta_min + beta_max) / 2).
                  Typically 0.5 (the random walk threshold).
    """

    atr_period: int = 14
    beta_min: float = 0.5
    beta_max: float = 3.0
    sigmoid_k: float = 10.0
    alpha_mid: float = 0.5

    def __post_init__(self):
        if not 5 <= self.atr_period <= 50:
            raise ValueError(f"atr_period must be between 5 and 50, got {self.atr_period}")
        if not 0.1 <= self.beta_min <= 2.0:
            raise ValueError(f"beta_min must be between 0.1 and 2.0, got {self.beta_min}")
        if not 1.0 <= self.beta_max <= 5.0:
            raise ValueError(f"beta_max must be between 1.0 and 5.0, got {self.beta_max}")
        if self.beta_min >= self.beta_max:
            raise ValueError(f"beta_min ({self.beta_min}) must be less than beta_max ({self.beta_max})")
        if not 1.0 <= self.sigmoid_k <= 50.0:
            raise ValueError(f"sigmoid_k must be between 1 and 50, got {self.sigmoid_k}")
        if not 0.3 <= self.alpha_mid <= 0.7:
            raise ValueError(f"alpha_mid must be between 0.3 and 0.7, got {self.alpha_mid}")


@dataclass
class RegimeConfig:
    """
    Configuration for market regime detection and smoothing.

    Uses EWMA (Exponentially Weighted Moving Average) with adaptive lambda
    to smooth the DFA alpha values and detect regime changes.

    Attributes:
        ewma_lambda_slow: Smoothing factor for stable regimes (close to 0 = very smooth).
                         Used when alpha changes are small.
        ewma_lambda_fast: Smoothing factor for regime transitions (higher = more reactive).
                         Used when alpha changes significantly.
        regime_change_threshold: Threshold for detecting regime change.
                                If |Δα| > threshold, use fast lambda.
        trending_threshold: Alpha value above which market is classified as trending.
        mean_reverting_threshold: Alpha value below which market is classified as mean-reverting.
    """

    ewma_lambda_slow: float = 0.05
    ewma_lambda_fast: float = 0.3
    regime_change_threshold: float = 0.1
    trending_threshold: float = 0.65
    mean_reverting_threshold: float = 0.35

    def __post_init__(self):
        if not 0.01 <= self.ewma_lambda_slow <= 0.2:
            raise ValueError(f"ewma_lambda_slow must be between 0.01 and 0.2, got {self.ewma_lambda_slow}")
        if not 0.1 <= self.ewma_lambda_fast <= 0.5:
            raise ValueError(f"ewma_lambda_fast must be between 0.1 and 0.5, got {self.ewma_lambda_fast}")
        if self.ewma_lambda_slow >= self.ewma_lambda_fast:
            raise ValueError("ewma_lambda_slow must be less than ewma_lambda_fast")
        if not 0.05 <= self.regime_change_threshold <= 0.3:
            raise ValueError(f"regime_change_threshold must be between 0.05 and 0.3, got {self.regime_change_threshold}")
        if not 0.55 <= self.trending_threshold <= 0.8:
            raise ValueError(f"trending_threshold must be between 0.55 and 0.8, got {self.trending_threshold}")
        if not 0.2 <= self.mean_reverting_threshold <= 0.45:
            raise ValueError(f"mean_reverting_threshold must be between 0.2 and 0.45, got {self.mean_reverting_threshold}")
        if self.mean_reverting_threshold >= self.trending_threshold:
            raise ValueError("mean_reverting_threshold must be less than trending_threshold")


@dataclass
class ConfidenceWeights:
    """
    Weights for confidence score components.

    The total confidence is calculated as:
    confidence = w1*k1 + w2*k2 + w3*k3 + w4*k4

    where:
    - k1: Threshold distance (how far amplitude exceeds threshold)
    - k2: Timeframe consistency (how many timeframes confirm the pivot)
    - k3: DFA stability (how stable alpha was during pivot formation)
    - k4: Structural validity (whether pivot fits the local structure)

    Weights should sum to approximately 1.0 for a 0-100 confidence scale.

    Attributes:
        w1_threshold_distance: Weight for threshold distance component.
        w2_timeframe_consistency: Weight for timeframe consistency component.
        w3_dfa_stability: Weight for DFA stability component.
        w4_structural_validity: Weight for structural validity component.
    """

    w1_threshold_distance: float = 0.30
    w2_timeframe_consistency: float = 0.35
    w3_dfa_stability: float = 0.15
    w4_structural_validity: float = 0.20

    def __post_init__(self):
        for name, value in [
            ("w1_threshold_distance", self.w1_threshold_distance),
            ("w2_timeframe_consistency", self.w2_timeframe_consistency),
            ("w3_dfa_stability", self.w3_dfa_stability),
            ("w4_structural_validity", self.w4_structural_validity),
        ]:
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1, got {value}")

        total = sum([
            self.w1_threshold_distance,
            self.w2_timeframe_consistency,
            self.w3_dfa_stability,
            self.w4_structural_validity,
        ])
        if not 0.95 <= total <= 1.05:
            raise ValueError(f"Weights should sum to approximately 1.0, got {total}")

    @property
    def as_tuple(self) -> tuple:
        """Return weights as a tuple (w1, w2, w3, w4)."""
        return (
            self.w1_threshold_distance,
            self.w2_timeframe_consistency,
            self.w3_dfa_stability,
            self.w4_structural_validity,
        )


@dataclass
class EngineConfig:
    """
    Complete configuration for the Wave Engine.

    This is the main configuration object that contains all sub-configurations.
    All parameters have sensible defaults suitable for daily stock analysis.

    Attributes:
        dfa: Configuration for DFA calculation.
        threshold: Configuration for adaptive threshold.
        regime: Configuration for regime detection.
        confidence_weights: Weights for confidence scoring.
        fibonacci_tolerance: Tolerance for Fibonacci ratio matching (±5% by default).
        enabled_timeframes: List of timeframes to analyze.
    """

    dfa: DFAConfig = field(default_factory=DFAConfig)
    threshold: ThresholdConfig = field(default_factory=ThresholdConfig)
    regime: RegimeConfig = field(default_factory=RegimeConfig)
    confidence_weights: ConfidenceWeights = field(default_factory=ConfidenceWeights)
    fibonacci_tolerance: float = 0.05
    enabled_timeframes: List[TimeframeLevel] = field(
        default_factory=lambda: [TimeframeLevel.D1]
    )

    def __post_init__(self):
        if not 0.01 <= self.fibonacci_tolerance <= 0.2:
            raise ValueError(f"fibonacci_tolerance must be between 0.01 and 0.2, got {self.fibonacci_tolerance}")
        if not self.enabled_timeframes:
            raise ValueError("At least one timeframe must be enabled")

    @classmethod
    def default(cls) -> "EngineConfig":
        """Create a default configuration."""
        return cls()

    @classmethod
    def sensitive(cls) -> "EngineConfig":
        """
        Create a sensitive configuration for detecting more pivots.

        Good for ranging/choppy markets or shorter-term analysis.
        """
        return cls(
            dfa=DFAConfig(window_size=100, polynomial_order=2),
            threshold=ThresholdConfig(beta_min=0.3, beta_max=2.0, alpha_mid=0.45),
            regime=RegimeConfig(ewma_lambda_fast=0.35),
        )

    @classmethod
    def conservative(cls) -> "EngineConfig":
        """
        Create a conservative configuration for detecting fewer, larger pivots.

        Good for trending markets or longer-term analysis.
        """
        return cls(
            dfa=DFAConfig(window_size=200, polynomial_order=2),
            threshold=ThresholdConfig(beta_min=0.8, beta_max=4.0, alpha_mid=0.55),
            regime=RegimeConfig(ewma_lambda_slow=0.03),
        )

    @classmethod
    def trending(cls) -> "EngineConfig":
        """
        Create a configuration optimized for trending markets.

        Uses a higher alpha_mid to be less sensitive in trending conditions.
        """
        return cls(
            threshold=ThresholdConfig(alpha_mid=0.6, beta_max=3.5),
            regime=RegimeConfig(trending_threshold=0.60),
        )

    @classmethod
    def mean_reverting(cls) -> "EngineConfig":
        """
        Create a configuration optimized for mean-reverting/ranging markets.

        Uses a lower alpha_mid to be more sensitive in ranging conditions.
        """
        return cls(
            threshold=ThresholdConfig(alpha_mid=0.4, beta_min=0.4),
            regime=RegimeConfig(mean_reverting_threshold=0.40),
        )

    def to_dict(self) -> dict:
        """Convert configuration to a dictionary for serialization."""
        return {
            "dfa": {
                "window_size": self.dfa.window_size,
                "polynomial_order": self.dfa.polynomial_order,
                "min_segment_size": self.dfa.min_segment_size,
                "max_segment_ratio": self.dfa.max_segment_ratio,
            },
            "threshold": {
                "atr_period": self.threshold.atr_period,
                "beta_min": self.threshold.beta_min,
                "beta_max": self.threshold.beta_max,
                "sigmoid_k": self.threshold.sigmoid_k,
                "alpha_mid": self.threshold.alpha_mid,
            },
            "regime": {
                "ewma_lambda_slow": self.regime.ewma_lambda_slow,
                "ewma_lambda_fast": self.regime.ewma_lambda_fast,
                "regime_change_threshold": self.regime.regime_change_threshold,
                "trending_threshold": self.regime.trending_threshold,
                "mean_reverting_threshold": self.regime.mean_reverting_threshold,
            },
            "confidence_weights": {
                "w1_threshold_distance": self.confidence_weights.w1_threshold_distance,
                "w2_timeframe_consistency": self.confidence_weights.w2_timeframe_consistency,
                "w3_dfa_stability": self.confidence_weights.w3_dfa_stability,
                "w4_structural_validity": self.confidence_weights.w4_structural_validity,
            },
            "fibonacci_tolerance": self.fibonacci_tolerance,
            "enabled_timeframes": [tf.value for tf in self.enabled_timeframes],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EngineConfig":
        """Create configuration from a dictionary."""
        return cls(
            dfa=DFAConfig(**data.get("dfa", {})) if data.get("dfa") else DFAConfig(),
            threshold=ThresholdConfig(**data.get("threshold", {})) if data.get("threshold") else ThresholdConfig(),
            regime=RegimeConfig(**data.get("regime", {})) if data.get("regime") else RegimeConfig(),
            confidence_weights=ConfidenceWeights(**data.get("confidence_weights", {})) if data.get("confidence_weights") else ConfidenceWeights(),
            fibonacci_tolerance=data.get("fibonacci_tolerance", 0.05),
            enabled_timeframes=[
                TimeframeLevel(tf) for tf in data.get("enabled_timeframes", ["1d"])
            ],
        )
