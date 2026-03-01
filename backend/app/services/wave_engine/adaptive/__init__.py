"""
Adaptive threshold and regime detection module.

Provides:
- Sigmoid mapping function for DFA alpha to threshold multiplier
- ATR-based adaptive threshold calculation
- Market regime detection with EWMA smoothing
"""

from .sigmoid import sigmoid_mapping, SigmoidMapper
from .threshold import AdaptiveThreshold, ThresholdResult
from .regime import RegimeDetector, RegimeState, RegimeType, RegimeChangeEvent

__all__ = [
    "sigmoid_mapping",
    "SigmoidMapper",
    "AdaptiveThreshold",
    "ThresholdResult",
    "RegimeDetector",
    "RegimeState",
    "RegimeType",
    "RegimeChangeEvent",
]
