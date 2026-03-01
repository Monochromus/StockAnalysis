"""
Enhanced pivot detection and management module.

Provides:
- Adaptive pivot detection using DFA-based thresholds
- Pivot lifecycle management (POTENTIAL → CONFIRMED → PROMOTED → INVALID)
- Confidence scoring with multiple components
"""

from .detector import AdaptivePivotDetector, EnhancedPivot, EnhancedPivotSequence
from .lifecycle import PivotLifecycleManager, PivotStatus
from .confidence import ConfidenceCalculator, ConfidenceComponents

__all__ = [
    "AdaptivePivotDetector",
    "EnhancedPivot",
    "EnhancedPivotSequence",
    "PivotLifecycleManager",
    "PivotStatus",
    "ConfidenceCalculator",
    "ConfidenceComponents",
]
