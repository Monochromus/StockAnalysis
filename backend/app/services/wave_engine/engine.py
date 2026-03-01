"""
Wave Engine - Main orchestrator for adaptive wave analysis.

This is the main entry point for the wave engine, coordinating:
- DFA calculation
- Adaptive threshold computation
- Regime detection
- Pivot detection with confidence scoring
- Integration with existing wave counting
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
import numpy as np

from .config import EngineConfig, TimeframeLevel
from .dfa import DFACalculator, DFAResult, RollingDFA
from .adaptive import (
    AdaptiveThreshold,
    ThresholdResult,
    RegimeDetector,
    RegimeState,
    RegimeType,
    RegimeChangeEvent,
)
from .pivot import (
    AdaptivePivotDetector,
    EnhancedPivot,
    EnhancedPivotSequence,
    PivotLifecycleManager,
    ConfidenceCalculator,
    PivotStatus,
)


@dataclass
class EngineState:
    """Internal state of the wave engine."""

    rolling_dfa: RollingDFA
    regime_detector: RegimeDetector
    adaptive_threshold: AdaptiveThreshold
    pivot_detector: AdaptivePivotDetector
    confidence_calculator: ConfidenceCalculator
    lifecycle_manager: PivotLifecycleManager


@dataclass
class AnalysisResult:
    """Complete result of wave engine analysis."""

    # DFA
    dfa_result: DFAResult
    alpha_history: List[float]

    # Regime
    regime_state: RegimeState
    regime_events: List[RegimeChangeEvent]

    # Threshold
    threshold_result: ThresholdResult

    # Pivots
    pivots: List[EnhancedPivot]
    pivot_sequence: EnhancedPivotSequence

    # Metadata
    symbol: str
    timestamp: datetime
    data_points: int
    config: EngineConfig


class WaveEngine:
    """
    Main wave engine for adaptive Elliott Wave analysis.

    Coordinates all components to provide:
    - DFA-based market regime detection
    - Adaptive threshold calculation
    - Enhanced pivot detection with confidence scoring

    Usage:
        engine = WaveEngine(config)
        result = engine.analyze(prices, highs, lows, closes, timestamps)
    """

    def __init__(self, config: Optional[EngineConfig] = None):
        """
        Initialize the wave engine.

        Args:
            config: Engine configuration. Uses defaults if not provided.
        """
        self.config = config or EngineConfig()
        self._state: Optional[EngineState] = None
        self._initialize_components()

    def _initialize_components(self):
        """Initialize all engine components with current config."""
        self._state = EngineState(
            rolling_dfa=RollingDFA(
                window_size=self.config.dfa.window_size,
                polynomial_order=self.config.dfa.polynomial_order,
                ewma_lambda_slow=self.config.regime.ewma_lambda_slow,
                ewma_lambda_fast=self.config.regime.ewma_lambda_fast,
                regime_change_threshold=self.config.regime.regime_change_threshold,
            ),
            regime_detector=RegimeDetector(
                trending_threshold=self.config.regime.trending_threshold,
                mean_reverting_threshold=self.config.regime.mean_reverting_threshold,
                ewma_lambda_slow=self.config.regime.ewma_lambda_slow,
                ewma_lambda_fast=self.config.regime.ewma_lambda_fast,
                regime_change_threshold=self.config.regime.regime_change_threshold,
            ),
            adaptive_threshold=AdaptiveThreshold(
                atr_period=self.config.threshold.atr_period,
                beta_min=self.config.threshold.beta_min,
                beta_max=self.config.threshold.beta_max,
                sigmoid_k=self.config.threshold.sigmoid_k,
                alpha_mid=self.config.threshold.alpha_mid,
            ),
            pivot_detector=AdaptivePivotDetector(),
            confidence_calculator=ConfidenceCalculator(
                w1=self.config.confidence_weights.w1_threshold_distance,
                w2=self.config.confidence_weights.w2_timeframe_consistency,
                w3=self.config.confidence_weights.w3_dfa_stability,
                w4=self.config.confidence_weights.w4_structural_validity,
            ),
            lifecycle_manager=PivotLifecycleManager(),
        )

    def reset(self):
        """Reset the engine state."""
        self._initialize_components()

    def update_config(self, config: EngineConfig):
        """
        Update the engine configuration.

        Args:
            config: New configuration to use.
        """
        self.config = config
        self._initialize_components()

    def analyze(
        self,
        prices: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        timestamps: List[datetime],
        symbol: str = "UNKNOWN",
        timeframe: str = "1d",
    ) -> AnalysisResult:
        """
        Perform complete wave analysis.

        Args:
            prices: Array of prices (typically close prices) for DFA.
            highs: Array of high prices.
            lows: Array of low prices.
            closes: Array of close prices.
            timestamps: List of timestamps.
            symbol: Ticker symbol.
            timeframe: Timeframe identifier.

        Returns:
            AnalysisResult with all analysis data.
        """
        if self._state is None:
            self._initialize_components()

        state = self._state

        # Step 1: Calculate DFA
        dfa_result = self._calculate_dfa(prices)

        # Step 2: Update rolling DFA and get smoothed alpha
        dfa_state = state.rolling_dfa.update(prices)
        alpha = dfa_state.ewma_alpha

        # Step 3: Update regime detection
        regime_state = state.regime_detector.update(alpha, timestamps[-1] if timestamps else datetime.now())
        regime = self._to_internal_regime(regime_state.current_regime)

        # Step 4: Calculate adaptive threshold
        threshold_result = state.adaptive_threshold.calculate(
            highs, lows, closes, alpha, closes[-1] if len(closes) > 0 else None
        )
        tau = threshold_result.tau

        # Step 5: Detect pivots
        pivot_sequence = state.pivot_detector.detect(
            highs=highs,
            lows=lows,
            closes=closes,
            timestamps=timestamps,
            tau=tau,
            alpha=alpha,
            regime=regime,
            timeframe=timeframe,
        )

        # Step 6: Calculate confidence for all pivots
        alpha_history = dfa_state.alpha_history
        pivots = state.confidence_calculator.batch_update_confidence(
            pivots=pivot_sequence.pivots,
            tau=tau,
            alpha_history=alpha_history,
            timeframe_confirmations=1,
            total_timeframes=len(self.config.enabled_timeframes),
        )

        # Step 7: Get valid pivot sequence
        valid_pivots = state.lifecycle_manager.get_valid_sequence(pivots)

        return AnalysisResult(
            dfa_result=dfa_result,
            alpha_history=alpha_history,
            regime_state=regime_state,
            regime_events=state.regime_detector.get_regime_events(),
            threshold_result=threshold_result,
            pivots=valid_pivots,
            pivot_sequence=EnhancedPivotSequence(
                pivots=valid_pivots,
                timeframe=timeframe,
                current_tau=tau,
                current_alpha=alpha,
                current_regime=regime,
                total_candles=len(prices),
            ),
            symbol=symbol,
            timestamp=datetime.now(),
            data_points=len(prices),
            config=self.config,
        )

    def _calculate_dfa(self, prices: np.ndarray) -> DFAResult:
        """Calculate full DFA result."""
        calculator = DFACalculator(
            polynomial_order=self.config.dfa.polynomial_order,
            min_segment_size=self.config.dfa.min_segment_size,
            max_segment_ratio=self.config.dfa.max_segment_ratio,
        )
        return calculator.calculate(prices)

    def _to_internal_regime(self, regime_type) -> RegimeType:
        """Convert regime detector's RegimeType to pivot detector's."""
        from .adaptive.regime import RegimeType as DetectorRegimeType
        from .pivot.detector import RegimeType as PivotRegimeType

        mapping = {
            DetectorRegimeType.TRENDING: PivotRegimeType.TRENDING,
            DetectorRegimeType.MEAN_REVERTING: PivotRegimeType.MEAN_REVERTING,
            DetectorRegimeType.RANDOM_WALK: PivotRegimeType.RANDOM_WALK,
        }
        return mapping.get(regime_type, PivotRegimeType.RANDOM_WALK)

    def get_dfa_only(
        self,
        prices: np.ndarray,
        timestamps: Optional[List[datetime]] = None,
    ) -> Tuple[DFAResult, RegimeState]:
        """
        Get only DFA and regime analysis.

        Useful for quick regime checks without full pivot detection.

        Args:
            prices: Array of prices.
            timestamps: Optional timestamps.

        Returns:
            Tuple of (DFAResult, RegimeState).
        """
        if self._state is None:
            self._initialize_components()

        state = self._state

        # Calculate DFA
        dfa_result = self._calculate_dfa(prices)

        # Update rolling DFA
        dfa_state = state.rolling_dfa.update(prices)

        # Get regime
        timestamp = timestamps[-1] if timestamps else datetime.now()
        regime_state = state.regime_detector.update(dfa_state.ewma_alpha, timestamp)

        return dfa_result, regime_state

    def get_threshold_only(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        alpha: float,
    ) -> ThresholdResult:
        """
        Get only threshold calculation.

        Args:
            highs: Array of high prices.
            lows: Array of low prices.
            closes: Array of close prices.
            alpha: DFA alpha value.

        Returns:
            ThresholdResult with threshold details.
        """
        if self._state is None:
            self._initialize_components()

        return self._state.adaptive_threshold.calculate(
            highs, lows, closes, alpha, closes[-1] if len(closes) > 0 else None
        )

    def explain_pivot(self, pivot: EnhancedPivot) -> str:
        """
        Generate a human-readable explanation for a pivot.

        Args:
            pivot: The pivot to explain.

        Returns:
            Explanation string.
        """
        conf_cat = ConfidenceCalculator.confidence_category(pivot.overall_confidence)

        explanation = [
            f"{'Swing High' if pivot.type.value == 'high' else 'Swing Low'} at {pivot.price:.2f}",
            f"Status: {pivot.status.value.upper()}",
            f"Confidence: {pivot.overall_confidence:.1f}/100 ({conf_cat.replace('_', ' ')})",
            "",
            "Context at detection:",
            f"  - DFA α: {pivot.alpha_at_creation:.3f} ({pivot.regime_at_creation.value})",
            f"  - Threshold τ: {pivot.tau_at_creation:.4f}",
            f"  - Amplitude: {pivot.amplitude:.4f} ({pivot.significance:.2f}%)",
        ]

        if pivot.confidence_components:
            explanation.extend([
                "",
                "Confidence breakdown:",
                f"  - Threshold distance (k1): {pivot.confidence_components['k1_threshold_distance']:.2f}",
                f"  - Timeframe consistency (k2): {pivot.confidence_components['k2_timeframe_consistency']:.2f}",
                f"  - DFA stability (k3): {pivot.confidence_components['k3_dfa_stability']:.2f}",
                f"  - Structural validity (k4): {pivot.confidence_components['k4_structural_validity']:.2f}",
            ])

        return "\n".join(explanation)

    def explain_regime(self, regime_state: RegimeState) -> str:
        """
        Generate a human-readable explanation for the current regime.

        Args:
            regime_state: Current regime state.

        Returns:
            Explanation string.
        """
        regime_descriptions = {
            "trending": "The market shows persistent trends. Price movements tend to continue in the same direction.",
            "mean_reverting": "The market shows mean-reverting behavior. Price movements tend to reverse.",
            "random_walk": "The market shows no significant pattern. Price movements are unpredictable.",
        }

        explanation = [
            f"Current Regime: {regime_state.current_regime.value.upper()}",
            "",
            regime_descriptions.get(regime_state.current_regime.value, "Unknown regime"),
            "",
            f"DFA α (smoothed): {regime_state.ewma_alpha:.3f}",
            f"DFA α (raw): {regime_state.current_alpha:.3f}",
            f"Regime strength: {regime_state.regime_strength}",
            f"Stability: {regime_state.stability_score:.2f}/1.00",
            f"Duration: {regime_state.regime_duration_bars} bars",
        ]

        return "\n".join(explanation)

    @classmethod
    def create_with_preset(cls, preset: str) -> "WaveEngine":
        """
        Create a wave engine with a predefined configuration preset.

        Args:
            preset: One of 'default', 'sensitive', 'conservative', 'trending', 'mean_reverting'.

        Returns:
            Configured WaveEngine instance.
        """
        presets = {
            "default": EngineConfig.default,
            "sensitive": EngineConfig.sensitive,
            "conservative": EngineConfig.conservative,
            "trending": EngineConfig.trending,
            "mean_reverting": EngineConfig.mean_reverting,
        }

        if preset not in presets:
            raise ValueError(f"Unknown preset: {preset}. Available: {list(presets.keys())}")

        return cls(presets[preset]())
