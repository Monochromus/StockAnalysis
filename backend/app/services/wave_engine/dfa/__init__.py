"""
Detrended Fluctuation Analysis (DFA) module.

Provides DFA-2 algorithm implementation for calculating the Hurst exponent (α)
which characterizes the long-range correlations in financial time series.
"""

from .calculator import DFACalculator, DFAResult
from .rolling import RollingDFA

__all__ = ["DFACalculator", "DFAResult", "RollingDFA"]
