"""
Adaptive Multi-Timeframe Wave Engine with Detrended Fluctuation Analysis.

This module provides sophisticated Elliott Wave analysis with:
- DFA-based market regime detection
- Adaptive thresholds that adjust to market conditions
- Multi-timeframe pivot hierarchy
- Confidence scoring for all detections
"""

from .config import EngineConfig, DFAConfig, ThresholdConfig, RegimeConfig, ConfidenceWeights

__all__ = [
    "EngineConfig",
    "DFAConfig",
    "ThresholdConfig",
    "RegimeConfig",
    "ConfidenceWeights",
]
