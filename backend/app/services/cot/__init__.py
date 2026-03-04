"""
COT (Commitments of Traders) Service Module.

This module provides functionality for fetching and analyzing CFTC COT data.
"""

from .cot_client import COTClient
from .cache import COTCache
from .mappings import COTMapping
from .analyzer import COTAnalyzer

__all__ = [
    "COTClient",
    "COTCache",
    "COTMapping",
    "COTAnalyzer",
]
